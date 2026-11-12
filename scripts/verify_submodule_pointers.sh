#!/usr/bin/env bash
set -e

# ==============================================================================
# verify_submodule_pointers.sh
# Valida se os ponteiros dos submódulos estão íntegros, sem regressões em relação
# à branch alvo (ex.: dev) e apontando para o commit mais recente da branch de trabalho.
#
# Uso:
#   ./scripts/verify_submodule_pointers.sh [--target-branch <branch>] [--head-branch <branch>]
# ==============================================================================

TARGET_BRANCH="dev"
HEAD_BRANCH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --head-branch)
      HEAD_BRANCH="$2"
      shift 2
      ;;
    *)
      echo "Opção desconhecida: $1"
      exit 1
      ;;
  esac
done

if [ -z "$HEAD_BRANCH" ]; then
  HEAD_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
fi

echo "=================================================================="
echo "      VERIFICAÇÃO DE PONTEIROS DE SUBMÓDULOS (OxeBots)"
echo "=================================================================="
echo "Target branch (base): $TARGET_BRANCH"
if [ -n "$HEAD_BRANCH" ]; then
  echo "Head branch (PR/local): $HEAD_BRANCH"
fi
echo "------------------------------------------------------------------"

HAS_ERROR=0

# Garante que temos as referências da target branch
git fetch --no-recurse-submodules origin "$TARGET_BRANCH" 2>/dev/null || true

for sub in $(git config --file .gitmodules --get-regexp path | awk '{print $2}'); do
    echo "🔍 Verificando submódulo: $sub"

    # 1. Obter o commit registrado no superprojeto (HEAD)
    pr_commit=$(git rev-parse HEAD:"$sub" 2>/dev/null || echo "")
    if [ -z "$pr_commit" ]; then
        echo "   ⚠️ Não foi possível obter o commit de $sub em HEAD."
        continue
    fi

    # 2. Verificar se há alterações não commitadas dentro da pasta do submódulo localmente
    if [ -d "$sub/.git" ] || [ -f "$sub/.git" ]; then
        local_head=$(git -C "$sub" rev-parse HEAD 2>/dev/null || echo "")
        if [ -n "$local_head" ] && [ "$local_head" != "$pr_commit" ]; then
            echo "   ❌ [ERRO] O HEAD local de '$sub' ($local_head) difere do ponteiro commitado ($pr_commit)!"
            echo "      -> Execute: git add $sub && git commit para atualizar o superprojeto."
            HAS_ERROR=1
        fi

        dirty=$(git -C "$sub" status --porcelain 2>/dev/null || true)
        if [ -n "$dirty" ]; then
            echo "   ⚠️ [AVISO] Há alterações não commitadas dentro de '$sub'."
        fi
    fi

    # Atualiza refs remotas do submódulo para checagem precisa
    git -C "$sub" fetch --unshallow origin "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null || \
    git -C "$sub" fetch origin "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null || true

    # 3. Verificar regressão contra a TARGET_BRANCH
    base_commit=$(git ls-tree origin/"$TARGET_BRANCH" "$sub" 2>/dev/null | awk '{print $3}' || true)
    if [ -n "$base_commit" ]; then
        git -C "$sub" fetch origin "$base_commit" 2>/dev/null || true
        if [ "$base_commit" = "$pr_commit" ]; then
            echo "   ✅ Sincronizado com origin/$TARGET_BRANCH (mesmo commit: ${pr_commit:0:7})"
        elif git -C "$sub" merge-base --is-ancestor "$base_commit" "$pr_commit" 2>/dev/null; then
            echo "   ✅ Atualizado (avanço da $TARGET_BRANCH: ${base_commit:0:7} -> ${pr_commit:0:7})"
        else
            echo "   ❌ [ERRO] O submódulo '$sub' está defasado/regrediu em relação à branch '$TARGET_BRANCH'!"
            echo "      Commit na base ($TARGET_BRANCH): $base_commit"
            echo "      Commit no PR:                $pr_commit"
            echo "      -> Execute 'git -C $sub merge origin/$TARGET_BRANCH' e commite o ponteiro."
            HAS_ERROR=1
        fi
    fi

    # 4. Verificar se o ponteiro está desatualizado em relação à branch do PR (mesmo nome)
    if [ -n "$HEAD_BRANCH" ]; then
        remote_head_branch_commit=$(git -C "$sub" rev-parse --verify --quiet "refs/remotes/origin/$HEAD_BRANCH" || true)
        if [ -n "$remote_head_branch_commit" ]; then
            if [ "$pr_commit" != "$remote_head_branch_commit" ]; then
                echo "   ❌ [ERRO] O submódulo '$sub' possui a branch 'origin/$HEAD_BRANCH' em ${remote_head_branch_commit:0:7},"
                echo "      mas o superprojeto aponta para o commit desatualizado ${pr_commit:0:7}!"
                echo "      -> Execute: git add $sub && git commit no repositório principal."
                HAS_ERROR=1
            else
                echo "   ✅ Ponteiro coincide com a ponta de origin/$HEAD_BRANCH (${pr_commit:0:7})"
            fi
        fi
    fi

    # 5. Se o commit do PR foi alterado (diferente da base), verificar se a branch remota de trabalho tem commits mais recentes
    if [ -n "$base_commit" ] && [ "$base_commit" != "$pr_commit" ]; then
        # Localiza branches remotas do submódulo que contenham esse commit (excluindo base/main/master/HEAD)
        candidate_branches=$(git -C "$sub" branch -r --contains "$pr_commit" 2>/dev/null | \
            grep -v "origin/$TARGET_BRANCH" | \
            grep -v "origin/dev" | \
            grep -v "origin/main" | \
            grep -v "origin/master" | \
            grep -v "HEAD" | \
            tr -d ' *' || true)

        for b in $candidate_branches; do
            tip=$(git -C "$sub" rev-parse "$b" 2>/dev/null || true)
            if [ -n "$tip" ] && [ "$tip" != "$pr_commit" ]; then
                # Verifica se o tip é um descendente direto de pr_commit (ou seja, a branch avançou além do ponteiro)
                if git -C "$sub" merge-base --is-ancestor "$pr_commit" "$tip" 2>/dev/null; then
                    echo "   ❌ [ERRO] O submódulo '$sub' está com ponteiro desatualizado em relação à branch remota '$b'!"
                    echo "      Commit apontado no superprojeto: $pr_commit"
                    echo "      Último commit na branch remota:  $tip"
                    echo "      -> Para corrigir: cd $sub && git checkout $b && git pull && cd .. && git add $sub && git commit"
                    HAS_ERROR=1
                fi
            fi
        done
    fi
done

echo "------------------------------------------------------------------"
if [ $HAS_ERROR -ne 0 ]; then
    echo "❌ Falha na verificação de submódulos: inconsistências ou defasagens detectadas."
    exit 1
fi

echo "✅ Todos os submódulos estão consistentes e atualizados!"
exit 0
