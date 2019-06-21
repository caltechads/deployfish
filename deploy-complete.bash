_deploy_completion() {
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _DEPLOY_COMPLETE=complete $1 ) )
    return 0
}

complete -F _deploy_completion -o default deploy;
