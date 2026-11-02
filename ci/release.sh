#!/bin/sh
# Run from repository root. All releases require an immutable image reference.
set -eu

action=${1:?usage: release.sh deploy|rollback namespace overlay}
namespace=${2:?namespace required}
deployment=${K8S_DEPLOY:-webapp}
state="$WORKSPACE/.release-$namespace"

image_ref() {
    digest=$(cat "$WORKSPACE/.image-digest")
    printf '%s\n' "$digest" | grep -Eq '^sha256:[0-9a-f]{64}$' || {
        echo 'Invalid or missing image digest' >&2; exit 1;
    }
    printf '%s@%s' "${FULL_IMG%:*}" "$digest"
}

case "$action" in
  deploy)
    overlay=${3:?overlay required}
    image=$(image_ref)
    mkdir -p "$state"
    # Rendering must succeed before any mutation; never pipe a failed renderer into apply.
    kubectl kustomize "$overlay" > "$state/template.yaml"
    grep -q IMAGE_PLACEHOLDER "$state/template.yaml"
    sed "s|IMAGE_PLACEHOLDER|$image|g" "$state/template.yaml" > "$state/rendered.yaml"
    diff_rc=0
    kubectl -n "$namespace" diff -f "$state/rendered.yaml" || diff_rc=$?
    [ "$diff_rc" -le 1 ] || { echo 'kubectl diff failed' >&2; exit "$diff_rc"; }
    # --ignore-not-found permits first install but preserves RBAC/network errors.
    kubectl -n "$namespace" get deployment "$deployment" --ignore-not-found \
      -o 'jsonpath={.spec.template.spec.containers[?(@.name=="webapp")].image}' > "$state/previous-image"
    printf '%s' "$image" > "$state/target-image"
    touch "$state/started"
    kubectl -n "$namespace" apply -f "$state/rendered.yaml"
    kubectl -n "$namespace" rollout status "deployment/$deployment" --timeout=300s
    ;;
  rollback)
    [ -f "$state/started" ] || { echo 'Deployment was not started; no rollback'; exit 0; }
    previous=$(cat "$state/previous-image")
    [ -n "$previous" ] || { echo 'First deployment has no previous image; manual recovery required' >&2; exit 1; }
    target=$(cat "$state/target-image")
    # A JSON Patch test makes the check-and-replace atomic. Do not undo a newer release.
    current=$(kubectl -n "$namespace" get deployment "$deployment" \
      -o 'jsonpath={.spec.template.spec.containers[0].name}')
    [ "$current" = webapp ] || { echo 'Unexpected container ordering; refusing rollback' >&2; exit 1; }
    printf '%s\n' "$previous" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9._/@:-]*$'
    kubectl -n "$namespace" patch deployment "$deployment" --type=json \
      -p "[{\"op\":\"test\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"$target\"},{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"$previous\"}]"
    kubectl -n "$namespace" rollout status "deployment/$deployment" --timeout=300s
    ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
