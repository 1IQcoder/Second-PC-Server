const $reposList = document.querySelector('.reposList__wrapper')


async function delete_account(button) {
    const blockId = button.dataset.id;
    const block = document.querySelector(`#${CSS.escape(blockId)}`);
    const username = block.dataset.username;

    const params = new URLSearchParams({ username: username })
    const res = await fetch(`${SERVER_URL}/api/delete-account?${params.toString()}`)
    if (!res.ok) {
        return console.log('errrrrrr');
    }
    block.remove()
    delete accountsSection.vars.accounts[username]

    const accountsStr = JSON.stringify(accountsSection.vars.accounts);
    window.localStorage.setItem('accounts', accountsStr);
}


async function git_pull(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)

    const params = new URLSearchParams({ 
        url: block.dataset.repo_url,
        branch: block.dataset.repo_branch,
        name: block.dataset.repo_name
    })

    fetch(`${SERVER_URL}/api/git-pull?${params.toString()}`, { method: 'GET' })
    .then(res => res.json())
    .then(res => {
        console.log(res);
    })
}


async function delete_repo(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)

    const params = new URLSearchParams({ name: block.dataset.repo_name })

    fetch(`${SERVER_URL}/api/delete-repo?${params.toString()}`, { method: 'GET' })
    .then(data => {
        if (!data.ok) {
            return console.log('err')
        }
        return data.json()
    })
    .then(res => {
        console.log(res);
        block.remove()
    })
}


async function docker_build(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)


}












