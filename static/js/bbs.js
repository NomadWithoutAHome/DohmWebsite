// BBS State Management
const BBSState = {
    currentMenu: 'LOGIN',
    handle: null,
    accessLevel: 0,
    userInputBuffer: '',
    stats: {
        usersOnline: 0,
        callsToday: 0,
        lastCaller: 'None'
    },
    chatMessages: [],
    chatUsers: new Set(),
    fileLibrary: {
        currentCategory: null,
        currentSubcategory: null,
        files: {}
    },
    passwordInput: false,
    registration: {
        handle: null,
        awaitingPassword: false
    }
};

// Terminal Configuration
const TermConfig = {
    rows: 25,
    cols: 80,
    cursorBlink: true,
    theme: {
        background: '#000000',
        foreground: '#39ff14',
        cursor: '#39ff14',
        cursorAccent: '#000000',
        selectionBackground: '#39ff14',
        selectionForeground: '#000000',
        fontSize: 18,
        fontFamily: 'VT323, monospace',
        letterSpacing: 1,
        lineHeight: 1.2
    },
    convertEol: true,
    scrollback: 1000
};

// Menu Screens
const Screens = {
    MAIN: `
\x1b[1;32m
┌──────────────────[ \x1b[1;37mDohm Industries BBS\x1b[1;32m ]──────────────────┐
│                                                                  │
│  [\x1b[1;37mM\x1b[1;32m] Message Boards     [\x1b[1;37mF\x1b[1;32m] File Areas     [\x1b[1;37mD\x1b[1;32m] Door Games   │
│  [\x1b[1;37mS\x1b[1;32m] Sysop Chat         [\x1b[1;37mQ\x1b[1;32m] Quit                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37mSELECTION: \x1b[1;36m`,

    LOGIN: `
\x1b[1;32m
┌──────────────────[ \x1b[1;37mWelcome to Dohm Industries\x1b[1;32m ]─────────────┐
│                                                                           │
│                  Enter your handle to continue or 'NEW' to register       │
│                                                                                 │
└──────────────────────────────────────────────────────────────────────── ┘

\x1b[1;37mHandle: \x1b[1;36m`,

    REGISTRATION: `
\x1b[1;32m
┌──────────────────[ \x1b[1;37mNew User Registration\x1b[1;32m ]───────────────────┐
│                                                                                  │
│  Choose a handle (3-20 characters)                                               │
│  Choose a password (min 6 characters)                                            │
│                                                                  │
│  Note: Sysop handle is reserved for system administrator         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37mHandle: \x1b[1;36m`,

    CHAT: `
\x1b[1;32m
┌──────────────────[ \x1b[1;37mSysop Chat\x1b[1;32m ]────────────────────────────┐
│                                                                  │
│  Users Online:                                                   │
│  \x1b[1;36m{{USERS}}\x1b[1;32m                                                   │
│                                                                  │
│  Type /quit to return to main menu                              │
│  Type /clear to clear screen                                    │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37m`
};

// Add to Screens object
Screens.FILE_MENU = `
\x1b[1;32m
┌──────────────────[ \x1b[1;37mFile Library\x1b[1;32m ]─────────────────────────┐
│                                                                  │
│  [\x1b[1;37m1\x1b[1;32m] Software - Applications and utilities                      │
│  [\x1b[1;37m2\x1b[1;32m] Text Files - Documents and text files                     │
│  [\x1b[1;37m3\x1b[1;32m] Images - Pictures and graphics                           │
│                                                                  │
│  [\x1b[1;37mU\x1b[1;32m] Upload File                                              │
│  [\x1b[1;37mQ\x1b[1;32m] Return to Main Menu                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37mSELECTION: \x1b[1;36m`,

Screens.FILE_CATEGORY = `
\x1b[1;32m
┌──────────────────[ \x1b[1;37m{{CATEGORY}}\x1b[1;32m ]──────────────────────────┐
│                                                                  │
{{SUBCATEGORIES}}
│                                                                  │
│  [\x1b[1;37mB\x1b[1;32m] Back to File Menu                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37mSELECTION: \x1b[1;36m`,

Screens.FILE_LIST = `
\x1b[1;32m
┌──────────────────[ \x1b[1;37m{{SUBCATEGORY}}\x1b[1;32m ]────────────────────────┐
│                                                                  │
{{FILES}}
│                                                                  │
│  [\x1b[1;37mB\x1b[1;32m] Back to Category Menu                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

\x1b[1;37mSELECTION: \x1b[1;36m`;

// Initialize terminal
const term = new Terminal(TermConfig);

// BBS Core Functions
const BBS = {
    init() {
        term.open(document.getElementById('terminal'));
        term.focus();
        this.showStartupSequence();
        this.setupInputHandler();
        this.updateStats();
        this.initChat();  // Initialize chat socket
    },

    async showStartupSequence() {
        term.write('\x1b[1;32mInitializing modem...\r\n');
        await this.delay(500);
        term.write('ATZ\r\n');
        await this.delay(300);
        term.write('OK\r\n');
        await this.delay(300);
        term.write('ATDT 1-900-DOHM-BBS\r\n');
        await this.delay(1000);
        
        // Modem connection sounds simulation
        term.write('\x1b[1;33mDIALING...\r\n');
        term.write('RING... RING...\r\n');
        await this.delay(800);
        term.write('\x1b[1;32mCARRIER DETECTED: 2400 BAUD\r\n');
        await this.delay(400);
        term.write('CONNECT 2400\r\n');
        await this.delay(300);
        
        // Negotiation sequence
        term.write('\x1b[1;36mNegotiating connection parameters...\r\n');
        await this.delay(400);
        term.write('PROTOCOL: ZMODEM-90\r\n');
        await this.delay(200);
        term.write('COMPRESSION: MNP5\r\n');
        await this.delay(200);
        term.write('ERROR CORRECTION: MNP4\r\n');
        await this.delay(200);
        term.write('TERMINAL: ANSI-BBS\r\n');
        await this.delay(500);

        // System information
        term.write('\x1b[1;32m\r\nConnecting to Dohm Industries BBS Node 1...\r\n');
        await this.delay(400);
        term.write('System: Dohm Industries TBBS v1.0\r\n');
        await this.delay(300);
        term.write('Location: Cyberspace, NET\r\n');
        await this.delay(300);
        term.write('Sysop: DOHMBOY\r\n');
        await this.delay(500);

        // Final connection
        term.write('\x1b[1;32m\r\nConnection established!\r\n');
        await this.delay(700);
        term.write('\x1b[2J\x1b[H'); // Clear screen
        
        // Show welcome screen
        term.write(`\x1b[1;32m
        ▓█████▄  ▒█████   ██░ ██  ███▄ ▄███▓    ▄▄▄▄    ▄▄▄▄     ██████ 
        ▒██▀ ██▌▒██▒  ██▒▓██░ ██▒▓██▒▀█▀ ██▒   ▓█████▄ ▓█████▄ ▒██    ▒ 
        ░██   █▌▒██░  ██▒▒██▀▀██░▓██    ▓██░   ▒██▒ ▄██▒██▒ ▄██░ ▓██▄   
        ░▓█▄   ▌▒██   ██░░▓█ ░██ ▒██    ▒██    ▒██░█▀  ▒██░█▀    ▒   ██▒
        ░▒████▓ ░ ████▓▒░░▓█▒░██▓▒██▒   ░██▒   ░▓█  ▀█▓░▓█  ▀█▓▒██████▒▒
         ▒▒▓  ▒ ░ ▒░▒░▒░  ▒ ░░▒░▒░ ▒░   ░  ░   ░▒▓███▀▒░▒▓███▀▒▒ ▒▓▒ ▒ ░
         ░ ▒  ▒   ░ ▒ ▒░  ▒ ░▒░ ░░  ░      ░   ▒░▒   ░ ▒░▒   ░ ░ ░▒  ░ ░
         ░ ░  ░ ░ ░ ░ ▒   ░  ░░ ░░      ░       ░    ░  ░    ░ ░  ░  ░  
           ░        ░ ░   ░  ░  ░       ░       ░      ░      ░       ░  
    \r\n`);
        await this.delay(1500);
        term.write(Screens.LOGIN);
    },

    setupInputHandler() {
        term.onData(e => {
            // Handle backspace
            if (e.charCodeAt(0) === 127) {
                if (BBSState.userInputBuffer.length > 0) {
                    BBSState.userInputBuffer = BBSState.userInputBuffer.slice(0, -1);
                    term.write('\b \b');
                }
                return;
            }

            // Handle enter key
            if (e === '\r' || e === '\n') {
                const command = BBSState.userInputBuffer;
                BBSState.userInputBuffer = '';
                term.write('\r\n');
                this.processCommand(command);
                return;
            }

            // Echo input
            if (e >= ' ' && e <= '~') {
                BBSState.userInputBuffer += e;
                // Only show asterisks if in password input mode
                term.write(BBSState.passwordInput ? '*' : e);
            }
        });
    },

    async processCommand(cmd) {
        switch(BBSState.currentMenu) {
            case 'LOGIN':
                if (cmd.toUpperCase() === 'NEW') {
                    BBSState.currentMenu = 'REGISTRATION';
                    BBSState.registration = { handle: null, awaitingPassword: false };
        term.write('\x1b[2J\x1b[H');
                    term.write(Screens.REGISTRATION);
                } else if (cmd.trim()) {
                    BBSState.handle = cmd;
                    BBSState.currentMenu = 'PASSWORD';
                    BBSState.passwordInput = true;
                    term.write('\x1b[1;37mPassword: \x1b[1;36m');
                }
                break;
            case 'PASSWORD':
                if (cmd.trim()) {
                    try {
                        const response = await fetch('/bbs/login', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                handle: BBSState.handle,
                                password: cmd
                            })
                        });
                        const data = await response.json();
                        
                        BBSState.passwordInput = false;
                        
                        if (response.ok) {
                            BBSState.handle = data.handle;
                            BBSState.accessLevel = data.accessLevel;
                            BBSState.currentMenu = 'MAIN';
                            await this.showMainMenu();
                        } else {
                            term.write('\x1b[1;31mInvalid credentials!\x1b[0m\r\n');
                            await this.delay(2000);
                            BBSState.currentMenu = 'LOGIN';
                            BBSState.handle = null;
        term.write('\x1b[2J\x1b[H');
                            term.write(Screens.LOGIN);
                        }
                    } catch (error) {
                        console.error('Login error:', error);
                        term.write('\x1b[1;31mLogin failed. Please try again.\x1b[0m\r\n');
                        await this.delay(2000);
                        BBSState.currentMenu = 'LOGIN';
                        BBSState.handle = null;
                        BBSState.passwordInput = false;
        term.write('\x1b[2J\x1b[H');
                        term.write(Screens.LOGIN);
                    }
                }
                break;
            case 'REGISTRATION':
                if (!BBSState.registration.handle) {
                    if (cmd.length < 3) {
                        term.write('\x1b[1;31mHandle must be at least 3 characters\x1b[0m\r\n');
                        term.write('\x1b[1;37mHandle: \x1b[1;36m');
                    } else {
                        BBSState.registration.handle = cmd;
                        BBSState.passwordInput = true;
                        term.write('\x1b[1;37mPassword: \x1b[1;36m');
                        BBSState.registration.awaitingPassword = true;
                    }
                } else if (BBSState.registration.awaitingPassword) {
                    if (cmd.length < 6) {
                        term.write('\x1b[1;31mPassword must be at least 6 characters\x1b[0m\r\n');
                        term.write('\x1b[1;37mPassword: \x1b[1;36m');
                    } else {
                        try {
                            const response = await fetch('/bbs/register', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    handle: BBSState.registration.handle,
                                    password: cmd
                                })
                            });
                            const data = await response.json();
                            
                            BBSState.passwordInput = false;
                            BBSState.registration = { handle: null, awaitingPassword: false };
                            
                            if (response.ok) {
                                term.write('\x1b[1;32mRegistration successful! Please login.\x1b[0m\r\n');
                                await this.delay(2000);
                                BBSState.currentMenu = 'LOGIN';
                                term.write('\x1b[2J\x1b[H');
                                term.write(Screens.LOGIN);
                            } else {
                                term.write(`\x1b[1;31m${data.error}\x1b[0m\r\n`);
                                await this.delay(2000);
                                BBSState.currentMenu = 'REGISTRATION';
                                term.write('\x1b[2J\x1b[H');
                                term.write(Screens.REGISTRATION);
                            }
                        } catch (error) {
                            console.error('Registration error:', error);
                            term.write('\x1b[1;31mRegistration failed. Please try again.\x1b[0m\r\n');
                            await this.delay(2000);
                            BBSState.currentMenu = 'REGISTRATION';
                            BBSState.passwordInput = false;
                            BBSState.registration = { handle: null, awaitingPassword: false };
                            term.write('\x1b[2J\x1b[H');
                            term.write(Screens.REGISTRATION);
                        }
                    }
                }
                break;
            case 'MAIN':
                await this.processMainMenuCommand(cmd);
                break;
            case 'CHAT':
                if (cmd.toLowerCase() === '/quit') {
                    BBSState.currentMenu = 'MAIN';
                    await this.showMainMenu();
                } else if (cmd.toLowerCase() === '/clear') {
                    term.write('\x1b[2J\x1b[H');
                    term.write(Screens.CHAT.replace('{{USERS}}', Array.from(BBSState.chatUsers).join(', ')));
                    BBSState.chatMessages.forEach(msg => term.write(msg + '\r\n'));
                } else if (cmd.trim()) {
                    await this.sendChatMessage(cmd);
                }
                break;
            case 'FILE_MENU':
                switch(cmd.toUpperCase()) {
                    case '1':
                        await this.showFileCategory('software');
                        break;
                    case '2':
                        await this.showFileCategory('text');
                        break;
                    case '3':
                        await this.showFileCategory('images');
                        break;
                    case 'U':
                        term.write('\x1b[1;31mUpload functionality coming soon!\x1b[0m\r\n');
                        await this.delay(2000);
                        await this.showFileLibrary();
                        break;
                    case 'Q':
                        BBSState.currentMenu = 'MAIN';
                        await this.showMainMenu();
                        break;
                    default:
                        term.write('\x1b[1;31mInvalid selection!\x1b[0m\r\n');
                        term.write('\r\n\x1b[1;37mSELECTION: \x1b[1;36m');
                }
                break;
            case 'FILE_CATEGORY':
                if (cmd.toUpperCase() === 'B') {
                    await this.showFileLibrary();
        } else {
                    const category = FILE_LIBRARY.categories[BBSState.fileLibrary.currentCategory];
                    const subcategories = Object.keys(category.subcategories);
                    const selection = parseInt(cmd) - 1;
                    
                    if (selection >= 0 && selection < subcategories.length) {
                        await this.showFileList(subcategories[selection]);
            } else {
                        term.write('\x1b[1;31mInvalid selection!\x1b[0m\r\n');
                        term.write('\r\n\x1b[1;37mSELECTION: \x1b[1;36m');
                    }
                }
                break;
            case 'FILE_LIST':
                if (cmd.toUpperCase() === 'B') {
                    await this.showFileCategory(BBSState.fileLibrary.currentCategory);
                } else {
                    const selection = parseInt(cmd) - 1;
                    if (selection >= 0 && selection < BBSState.fileLibrary.files.length) {
                        const file = BBSState.fileLibrary.files[selection];
                        term.write(`\x1b[1;32mDownloading ${file.filename}...\x1b[0m\r\n`);
                        window.open(file.blob_url, '_blank');
                        await this.delay(2000);
                        await this.showFileList(BBSState.fileLibrary.currentSubcategory);
                    } else {
                        term.write('\x1b[1;31mInvalid selection!\x1b[0m\r\n');
                        term.write('\r\n\x1b[1;37mSELECTION: \x1b[1;36m');
                    }
                }
                break;
        }
    },

    async showMainMenu() {
    term.write('\x1b[2J\x1b[H');
        term.write(Screens.MAIN);
    },

    async processMainMenuCommand(cmd) {
        switch(cmd.toUpperCase()) {
            case 'M':
                term.write('\x1b[1;32mAccessing Message Boards...\r\n');
                await this.delay(1000);
                await this.showMessageBoards();
                break;
            case 'F':
                term.write('\x1b[1;32mAccessing File Library...\r\n');
                await this.delay(1000);
                await this.showFileLibrary();
                break;
            case 'D':
                term.write('\x1b[1;32mAccessing Door Games...\r\n');
                await this.delay(1000);
                await this.showDoorGames();
                break;
            case 'S':
                term.write('\x1b[1;32mAccessing Sysop Chat...\r\n');
                await this.delay(1000);
                await this.showChat();
                break;
            case 'Q':
                await this.handleQuit();
                break;
            default:
                term.write('\x1b[1;31mInvalid selection!\x1b[0m\r\n');
                await this.delay(1000);
                await this.showMainMenu();
                break;
        }
    },

    async handleQuit() {
        term.write('\r\n\x1b[1;31mDisconnecting...\r\n');
        await this.delay(1000);
        term.write('\x1b[2J\x1b[H');
        term.write('\x1b[1;32mThank you for visiting Dohm Industries BBS!\r\n');
        BBSState.currentMenu = 'LOGIN';
        await this.delay(2000);
        this.showStartupSequence();
    },

    updateStats() {
        document.getElementById('users-online').textContent = BBSState.stats.usersOnline;
        document.getElementById('calls-today').textContent = BBSState.stats.callsToday;
        document.getElementById('last-caller').textContent = BBSState.stats.lastCaller;
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    async initChat() {
        const clientId = Math.random().toString(36).substring(7);
        const eventSource = new EventSource(`/bbs/chat/stream?client_id=${clientId}`);
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'users_update') {
                BBSState.chatUsers = new Set(data.users);
                if (BBSState.currentMenu === 'CHAT') {
                    this.updateChatUserList();
                }
            } else {
                this.writeChatMessage(`\x1b[1;36m${data.from}\x1b[0m: ${data.message}`);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            eventSource.close();
            setTimeout(() => this.initChat(), 5000); // Reconnect after 5 seconds
        };

        // Get initial active users
        try {
            const response = await fetch('/bbs/chat/users');
            const users = await response.json();
            BBSState.chatUsers = new Set(users);
            if (BBSState.currentMenu === 'CHAT') {
                this.updateChatUserList();
            }
        } catch (error) {
            console.error('Error fetching users:', error);
        }
    },

    async sendChatMessage(message) {
        try {
            await fetch('/bbs/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    handle: BBSState.handle,
                    message: message
                })
            });
        } catch (error) {
            console.error('Error sending message:', error);
            this.writeChatMessage('\x1b[1;31mError sending message. Please try again.\x1b[0m');
        }
    },

    writeChatMessage(message) {
        BBSState.chatMessages.push(message);
        if (BBSState.currentMenu === 'CHAT') {
            term.write(message + '\r\n');
        }
    },

    updateChatUserList() {
        // Save cursor position
        term.write('\x1b7');
        // Move to users line and clear it
        term.write('\x1b[3;1H');
        term.write('\x1b[2K');
        // Write updated user list
        term.write('  \x1b[1;36m' + Array.from(BBSState.chatUsers).join(', ') + '\x1b[0m');
        // Restore cursor position
        term.write('\x1b8');
    },

    async showFileLibrary() {
        BBSState.currentMenu = 'FILE_MENU';
    term.write('\x1b[2J\x1b[H');
        term.write(Screens.FILE_MENU);
    },

    async showFileCategory(category) {
        BBSState.currentMenu = 'FILE_CATEGORY';
        BBSState.fileLibrary.currentCategory = category;
        
        const categoryInfo = FILE_LIBRARY.categories[category];
        let subcategoriesText = '';
        let index = 1;
        
        for (const [key, name] of Object.entries(categoryInfo.subcategories)) {
            subcategoriesText += `│  [\x1b[1;37m${index}\x1b[1;32m] ${name.padEnd(45)}│\n`;
            index++;
        }

        term.write('\x1b[2J\x1b[H');
        term.write(Screens.FILE_CATEGORY
            .replace('{{CATEGORY}}', categoryInfo.name)
            .replace('{{SUBCATEGORIES}}', subcategoriesText));
    },

    async showFileList(subcategory) {
        BBSState.currentMenu = 'FILE_LIST';
        BBSState.fileLibrary.currentSubcategory = subcategory;
        
        try {
            const response = await fetch(`/bbs/archive/${BBSState.fileLibrary.currentCategory}/${subcategory}`);
            const files = await response.json();
            BBSState.fileLibrary.files = files;

            let filesText = '';
            files.forEach((file, index) => {
                filesText += `│  [\x1b[1;37m${index + 1}\x1b[1;32m] ${file.filename.padEnd(35)} ${file.size.padEnd(8)} │\n`;
            });

            if (files.length === 0) {
                filesText = '│  No files found in this category                               │\n';
            }

            term.write('\x1b[2J\x1b[H');
            term.write(Screens.FILE_LIST
                .replace('{{SUBCATEGORY}}', FILE_LIBRARY.categories[BBSState.fileLibrary.currentCategory].subcategories[subcategory])
                .replace('{{FILES}}', filesText));
        } catch (error) {
            term.write('\x1b[1;31mError loading files. Please try again.\x1b[0m\r\n');
            await this.delay(2000);
            await this.showFileCategory(BBSState.fileLibrary.currentCategory);
        }
    },

    async showRegistration() {
        BBSState.currentMenu = 'REGISTRATION';
        BBSState.registration = { handle: null, awaitingPassword: false };
        term.write('\x1b[2J\x1b[H'); // Clear screen
        term.write(Screens.REGISTRATION);
    },

    async showMessageBoards() {
        term.write('\x1b[2J\x1b[H');
        term.write('\x1b[1;31mMessage Boards coming soon!\x1b[0m\r\n');
        await this.delay(2000);
        await this.showMainMenu();
    },

    async showDoorGames() {
        term.write('\x1b[2J\x1b[H');
        term.write('\x1b[1;31mDoor Games coming soon!\x1b[0m\r\n');
        await this.delay(2000);
        await this.showMainMenu();
    },

    async showChat() {
        BBSState.currentMenu = 'CHAT';
        term.write('\x1b[2J\x1b[H'); // Clear screen
        term.write(Screens.CHAT.replace('{{USERS}}', Array.from(BBSState.chatUsers).join(', ')));
        term.write('\x1b[1;32mConnected to chat. Type your message and press Enter.\r\n');
        term.write('Type /quit to return to main menu, /clear to clear screen.\x1b[0m\r\n\r\n');
    },
};

// Initialize BBS when document is ready
window.addEventListener('DOMContentLoaded', () => BBS.init()); 