const pullrepoButton = document.getElementById('pullrepoButton')
const clearreposButton = document.getElementById('clearreposButton')
const addNewRepoButton = document.getElementById('addNewRepoButton')
const closeNewRepoButton = document.getElementById('closeNewRepoButton')
closeNewRepoButton.style.display = 'none'
const addNewRepoWrapper = document.getElementById('addNewRepoWrapper')
addNewRepoWrapper.style.display = 'none'
const reposList = document.getElementById('reposList')
const terminalMessageWrapper = document.getElementById('terminalMessageWrapper')
const clearTerminalButton = document.getElementById('clearTerminalButton')


function addNewRepo(url, branch) {
    const blockId = Date.now()
    const repo_name = (url.slice(url.lastIndexOf('.com/')+5, url.length-4)).replace('/', '.') + '.' + branch
    reposList.innerHTML += `
        <br>
        <div id="${blockId}" class="repoElem" data-repo_url="${url}" data-repo_name="${repo_name}" data-repo_branch="${branch}">
            <h3>${repo_name} (${branch})</h3>
            <a href="${url}">GitHub Repo</a>
            <div>
                <span>docker status</span>
            </div>
            <div class="buttonsWrapper">
                <button class="git_pull" data-id="${blockId}" onclick="git_pull(this)">git pull</button>
                <button class="docker_build" data-id="${blockId}" onclick="docker_build(this)">docker build</button>
                <button class="docker_run" data-id="${blockId}" onclick="docker_run(this)">docker run</button>
                <button class="pull_and_run" data-id="${blockId}" onclick="pull_and_run(this)">pull and run</button>
                <button class="delete-repo" data-id="${blockId}" onclick="delete_repo(this)" style="background-color: red;">delete</button>
            </div>
        </div>
    `
}

var addRepoState = false
const newRepoWrapErrMsg = addNewRepoWrapper.querySelector('.errMsg')

const repoUrlSelect = addNewRepoWrapper.querySelector('select[name="branch"]')

function appendOption(value, text) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = text;
    repoUrlSelect.appendChild(option);
}

repoUrlSelect.addEventListener('focus', () => {
    const repo_url = addNewRepoWrapper.querySelector('input[name="repo_url"]')?.value
    const parsed_url = repo_url.slice(repo_url.lastIndexOf('.com/')+5, repo_url.length-4)
    
    fetch(`https://api.github.com/repos/${parsed_url}/branches`)
    .then(res => {
        repoUrlSelect.innerHTML = ''
        appendOption('1', 'loading...')
        return res.json()
    })
    .then(res => {
        repoUrlSelect.innerHTML = ''
        if (res.length == 0) {
            appendOption('1', 'emty')
            return;
        }
        res?.forEach(e => {
            appendOption(e.name, e.name)
        });
    })
})

closeNewRepoButton.addEventListener('click', () => {
    addNewRepoWrapper.style.display = 'none'
    addRepoState = false
    addNewRepoButton.textContent = 'Add repository'
    closeNewRepoButton.style.display = 'none'
})

addNewRepoButton.addEventListener('click', () => {
    console.log(addRepoState);
    if (addRepoState && addNewRepoWrapper.style.display == 'none') {
        addNewRepoWrapper.style.display = 'none'
        addRepoState = false
    } else if (!addRepoState && addNewRepoWrapper.style.display == 'none') {
        addNewRepoButton.textContent = 'Confirm ✓'
        closeNewRepoButton.style.display = 'block'
        addRepoState = true
        addNewRepoWrapper.style.display = 'flex'
    } else {
        const repo_url = addNewRepoWrapper.querySelector('input[name="repo_url"]')?.value
        const branch = addNewRepoWrapper.querySelector('select[name="branch"]')?.value

        if (!repo_url || !branch) {
            newRepoWrapErrMsg.textContent = 'url and branch are require'
            return;
        }

        addNewRepo(repo_url, branch)
        addNewRepoWrapper.style.display = 'none'
        closeNewRepoButton.style.display = 'none'
        addRepoState = false
        addNewRepoButton.textContent = 'Add repository'
    }
})

// terminalMessageWrapper
class Terminal {
    static addMsg(status, msg) {
        const now = new Date();
        const formatted = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        
        let msgType
        if (status == 200 || status == 'ok') {
            msgType = 'ok'
        } else if (status == 400 || status == 'err') {
            msgType = 'err'
        } else if (status == 'warn') {
            msgType = 'warn'
        }

        terminalMessageWrapper.innerHTML += `
            <div class="${msgType}">
                <span>[${formatted}] </span><span>${msg}</span>
            </div>
        `
    }
}

Terminal.addMsg(200, 'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Voluptate, minus magnam et ullam totam hic eligendi velit ex quam a odio obcaecati, laudantium neque veniam nisi incidunt! Esse, vel dolores!')

clearTerminalButton.addEventListener('click', () => {
    terminalMessageWrapper.innerHTML = ''
})