

class ReposList {
    constructor(selector) {
        this.section = document.querySelector(selector);

        this.vars = {
            isNewRepoSectionOpen: false
        }

        this.elements = {
            repos_wrapper: this.section.querySelector('.reposList__wrapper'),
            newRepo_wrapper: this.section.querySelector('.reposList__newRepoWrapper'),
            newRepo_addButton: this.section.querySelector('#reposList__addRepoButton'),
            newRepo_closeButton: this.section.querySelector('#reposList__closeRepoButton'),
            newRepo_errMsg: this.section.querySelector('.reposLis__newRepoWrapper__errMsg'),
            newRepo_urlInput: this.section.querySelector(' input[name="repo_url"]'),
            newRepo_branchSelect: this.createBranchSelectProxy(),
        };

        this.init();
    }

    init() {
        this.elements.newRepo_closeButton.style.display = 'none'
        this.elements.newRepo_wrapper.style.display = 'none'

        this.elements.newRepo_branchSelect.e.addEventListener('focus', e => this.handleBranchSelect(e))
        this.elements.newRepo_closeButton.addEventListener('click', () => this.handleCloseButton())
        this.elements.newRepo_addButton.addEventListener('click', () => this.handleAddButton())
    }

    // FUNCTIONS
    createBranchSelectProxy() {
        const self = this;
        const select = self.section.querySelector('select[name="branch"]');

        return {
            get e() {
                return select
            },

            appendOption(value, text, clear=false) {
                if (clear) {
                    select.innerHTML = ''
                }
                const option = document.createElement('option');
                option.value = value;
                option.textContent = text;
                select.appendChild(option);
            },

            clearOptions() {
                select.innerHTML = ''
            }
        };
    }

    async spawnRepo(url, branch) {
        const blockId = Date.now()
        const repo_name = (url.slice(url.lastIndexOf('.com/')+5, url.length-4)).replace('/', '.') + '.' + branch
        this.elements.repos_wrapper.innerHTML += `
            <br>
            <div id="${blockId}" class="reposList__wrapper__elem" data-repo_url="${url}" data-repo_name="${repo_name}" data-repo_branch="${branch}">
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

    // EVENT LISTENERS
    handleBranchSelect(e) {
        const select = this.elements.newRepo_branchSelect
        const repo_url = this.elements.newRepo_urlInput.value
    
        if (!repo_url) {
            this.elements.newRepo_errMsg.textContent = 'invalid repository url'
            return;
        }
    
        const parsed_url = repo_url.slice(repo_url.lastIndexOf('.com/')+5, repo_url.length-4)
    
        fetch(`https://api.github.com/repos/${parsed_url}/branches`)
        .then(res => {
            if (!res.ok) {
                select.appendOption('1', 'error occured');
                return Promise.reject('bad responce');
            }
            select.appendOption('1', 'loading...');
            return res.json();
        })
        .then(res => {
            select.clearOptions()
            if (res.length == 0) {
                this.elements.newRepo_errMsg.textContent = 'this repository have no branch';
                return;
            }
            res?.forEach(e => {
                select.appendOption(e.name, e.name);
            });
        })
        .catch(err => {
            this.elements.newRepo_errMsg.textContent = err;
        })
    }

    handleCloseButton() {
        this.elements.newRepo_wrapper.style.display = 'none'
        this.vars.isNewRepoSectionOpen = false
        this.elements.newRepo_addButton.textContent = 'Add repository'
        this.elements.newRepo_closeButton.style.display = 'none'
    }

    handleAddButton() {
        const vars = this.vars;
        const wrapper = this.elements.newRepo_wrapper;

        if (vars.isNewRepoSectionOpen && wrapper.style.display == 'none') {
            wrapper.style.display = 'none'
            vars.isNewRepoSectionOpen = false
        } else if (!vars.isNewRepoSectionOpen && wrapper.style.display == 'none') {
            this.elements.newRepo_addButton.textContent = 'Confirm ✓'
            reposList__closeRepoButton.style.display = 'block'
            vars.isNewRepoSectionOpen = true
            wrapper.style.display = 'flex'
        } else {
            const repo_url = this.elements.newRepo_urlInput.value;
            const branch = this.elements.newRepo_branchSelect.e.value;
            console.log(repo_url);
            console.log(branch);
            if (!repo_url || !branch) {
                this.elements.newRepo_errMsg.textContent = 'url and branch are required'
                return;
            }
    
            this.spawnRepo(repo_url, branch)
            wrapper.style.display = 'none'
            this.elements.newRepo_closeButton.style.display = 'none'
            vars.isNewRepoSectionOpen = false
            this.elements.newRepo_addButton.textContent = 'Add repository'
        }
    }
    
}
const reposListSection = new ReposList('.reposList');



// terminalMessageWrapper
class Terminal {
    constructor(selector) {
        this.section = document.querySelector(selector);

        this.vars = {
            isResizing: false
        }

        this.elements = {
            msgWrapper: this.section.querySelector('.terminal_messagesWrapper'),
            clearButton: this.section.querySelector('.terminal__clearButton'),
            resizer: this.section.querySelector('#terminal_resizer'),
        }

        this.resizeTerminal = this.resizeTerminal.bind(this);
        this.stopResizeTerminal = this.stopResizeTerminal.bind(this);

        this.init();
    }

    init() {
        this.elements.clearButton.addEventListener('click', () => this.handleClearButton());
        this.elements.resizer.addEventListener('mousedown', () => this.handleResizer());
    }

    // FUNCTIONS
    addMsg(status, msg) {
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

        this.elements.msgWrapper.innerHTML += `
            <div class="${msgType}">
                <span>[${formatted}] </span><span>${msg}</span>
            </div>
        `
    }

    resizeTerminal(e) {
        if (!this.vars.isResizing) return;

        const newHeight = window.innerHeight - e.clientY;
        this.section.style.height = `${newHeight}px`;
    }

    stopResizeTerminal() {
        this.vars.isResizing = false;
        document.body.style.cursor = '';
        document.removeEventListener('mousemove', this.resizeTerminal);
        document.removeEventListener('mouseup', this.stopResizeTerminal);
    }

    // EVENT LISTENERS
    handleClearButton() {
        this.elements.msgWrapper.innerHTML = ''
    }

    handleResizer() {
        this.vars.isResizing = true
        document.addEventListener('mousemove', this.resizeTerminal)
        document.addEventListener('mouseup', this.stopResizeTerminal)
    }
}

const terminal = new Terminal('.terminal');
// terminal.addMsg(200, 'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Voluptate, minus magnam et ullam totam hic eligendi velit ex quam a odio obcaecati, laudantium neque veniam nisi incidunt! Esse, vel dolores!')


