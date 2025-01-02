const $reposList = document.querySelector('.reposList__wrapper')

async function fullLaunch(button) {
    const params = new URLSearchParams({ repo_name: button.dataset.repo });
    const res = await fetch(`${SERVER_URL}/api/full-launch?${params.toString()}`, { method: 'GET' });
    const resData = await res.json();
}

async function switchRepoSettings(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);
    const settingsBlock = block.querySelector('.reposList__wrapper__elem__settings');

    if (settingsBlock.style.display == 'none' || settingsBlock.style.display == '') {
        settingsBlock.style.display = 'flex';
    } else {
        settingsBlock.style.display = 'none';
    }
}

async function delete_account(button) {
    const blockId = button.dataset.id;
    const block = document.querySelector(`#${CSS.escape(blockId)}`);
    const username = block.dataset.username;

    const params = new URLSearchParams({ username: username })
    const res = await fetch(`${SERVER_URL}/api/delete-account?${params.toString()}`)
    const resData = await res.json();
    if (!res.ok) {
        terminal.addMsg(400, resData.message)
        return;
    }
    block.remove()
    delete accountsSection.vars.accounts[username]

    const accountsStr = JSON.stringify(accountsSection.vars.accounts);
    window.localStorage.setItem('accounts', accountsStr);
    terminal.addMsg(200, resData.message)
}


async function git_pull(button) {
    const blockId = button.dataset.id
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`)

    const params = new URLSearchParams({ 
        url: block.dataset.repo_url,
        branch: block.dataset.repo_branch,
        name: block.dataset.repo_name
    })

    const res = await fetch(`${SERVER_URL}/api/git-pull?${params.toString()}`, { method: 'GET' })
    const resData = await res.json();
    terminal.addMsg(res.status, resData.message)
}


async function delete_repo(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);

    const params = new URLSearchParams({ name: button.dataset.repo });

    const res = await fetch(`${SERVER_URL}/api/delete-repo?${params.toString()}`, { method: 'GET' });
    const resData = await res.json();
    if (res.ok) {
        block.remove();
    }
    terminal.addMsg(res.status, resData.message);
}


async function docker_build(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);
    const repo_name = block.dataset.repo_name;

    const params = new URLSearchParams({ repo_name: repo_name });

    const res = await fetch(`${SERVER_URL}/api/docker-build?${params.toString()}`);
    const resData = await res.json();
    terminal.addMsg(res.status, resData.message);
}


async function docker_run(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);
    const repo_name = block.dataset.repo_name;
    const pathToDockerFile = reposListSection.vars.repos[repo_name].pathToDockerFile;

    const params = new URLSearchParams({ repo_name: repo_name });
    const res = await fetch(`${SERVER_URL}/api/docker-run?${params.toString()}`);
    const resData = await res.json();
    terminal.addMsg(res.status, resData.message);
}


async function updateBuildCommand(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);
    const repoName = block.dataset.repo_name;
    const newBuildCommand = block.querySelector(' input[name="buildCommandInput"]');
    console.log(newBuildCommand);

    const params = new URLSearchParams({
        repo_name: repoName,
        update: JSON.stringify({ 'docker/buildCommand': newBuildCommand.value })
    });

    const res = await fetch(`${SERVER_URL}/api/update-repo-info?${params.toString()}`);
    const resData = await res.json();
    console.log(resData);
}








