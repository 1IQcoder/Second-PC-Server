const $reposList = document.getElementById('reposList')

async function git_pull(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)

    const params = new URLSearchParams({ 
        url: block.dataset.repo_url,
        branch: block.dataset.repo_branch,
        name: block.dataset.repo_name
    })

    fetch(`http://127.0.0.1:3000/api/git-pull?${params.toString()}`, { method: 'GET' })
    .then(res => res.json())
    .then(res => {
        console.log(res);
    })
}


async function delete_repo(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)

    const params = new URLSearchParams({ name: block.dataset.repo_name })

    fetch(`http://127.0.0.1:3000/api/delete-repo?${params.toString()}`, { method: 'GET' })
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















