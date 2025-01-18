const $reposList = document.querySelector('.reposList__wrapper')

// скрывает/раскрывает контент сообщения-блока в консоли
async function hideContent(button) {
    const isVisible = button.dataset.hide;
    const id = button.dataset.id;
    const block = terminal.elements.msgWrapper.querySelector(`#${CSS.escape(id)}`);
    const block_content = block.querySelector('.block_content')
    if (!isVisible || isVisible == 'false') {
        block_content.style.display = 'none';
        button.dataset.hide = 'true';
    } else {
        block_content.style.display = 'flex';
        button.dataset.hide = 'false';
    }
}

async function fullLaunch(button) {
    const params = new URLSearchParams({ repo_name: button.dataset.repo });
    sseConnection('/api/full-launch', params)
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


async function delete_repo(button) {
    const blockId = button.dataset.id;
    const block = $reposList.querySelector(`#${CSS.escape(blockId)}`);

    const params = new URLSearchParams({ name: button.dataset.repo });

    const res = await fetch(`${SERVER_URL}/api/delete-repo?${params.toString()}`, { method: 'GET' });
    const resData = await res.json();
    if (res.ok) {
        block.remove();
    }
    terminal.addMsg(res.status, resData.msg);
}









