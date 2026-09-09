console.debug("[init] script.js loading...")
const PLAY_ICONS_DOM = `
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
    class="volume0 icon icon-tabler icons-tabler-outline icon-tabler-volume">
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path
        d="M6 15h-2a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1h2l3.5 -4.5a.8 .8 0 0 1 1.5 .5v14a.8 .8 0 0 1 -1.5 .5l-3.5 -4.5" />
</svg>
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
    class="volume1 icon icon-tabler icons-tabler-outline icon-tabler-volume">
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path d="M15 8a5 5 0 0 1 0 8" />
    <path
        d="M6 15h-2a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1h2l3.5 -4.5a.8 .8 0 0 1 1.5 .5v14a.8 .8 0 0 1 -1.5 .5l-3.5 -4.5" />
</svg>
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
    class="volume2 icon icon-tabler icons-tabler-outline icon-tabler-volume">
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path d="M15 8a5 5 0 0 1 0 8" />
    <path d="M17.7 5a9 9 0 0 1 0 14" />
    <path
        d="M6 15h-2a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1h2l3.5 -4.5a.8 .8 0 0 1 1.5 .5v14a.8 .8 0 0 1 -1.5 .5l-3.5 -4.5" />
</svg>
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
    class="volume-1 icon icon-tabler icons-tabler-outline icon-tabler-volume-off">
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path d="M15 8a5 5 0 0 1 1.912 4.934m-1.377 2.602a5 5 0 0 1 -.535 .464" />
    <path d="M17.7 5a9 9 0 0 1 2.362 11.086m-1.676 2.299a9 9 0 0 1 -.686 .615" />
    <path
        d="M9.069 5.054l.431 -.554a.8 .8 0 0 1 1.5 .5v2m0 4v8a.8 .8 0 0 1 -1.5 .5l-3.5 -4.5h-2a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1h2l1.294 -1.664" />
    <path d="M3 3l18 18" />
</svg>
`;

const isWebKitGTK = /Linux/.test(navigator.userAgent)
    && /AppleWebKit/.test(navigator.userAgent)
    && !/Chrome|Edg/.test(navigator.userAgent);
if (isWebKitGTK) document.documentElement.classList.add("is-webkitgtk");

initScrollbarToggle();
document.addEventListener("dragstart", (event) => event.preventDefault());

window.addEventListener("pywebviewready", initApp);
function initApp() {
    initSidebarResizer();
    initSidebarToggle();
    initSidebarSectionsToggle();
    initThemeToggle();
    displayCurrentSource();
    displayDictSourcesList();
    document.getElementById("query-input").focus();
    console.debug("[init] app initialising finished");
}

async function initSidebarResizer() {
    const resizer = document.querySelector(".sidebar__resizer");
    if (!resizer) return;
    const body = document.body;

    body.classList.add("u-no-transition");
    const sidebarWidth = await pywebview.api.storage_get("sidebarWidth");
    if (sidebarWidth) body.style.setProperty("--sidebar-width", `${sidebarWidth}px`);
    body.classList.remove("u-no-transition");

    resizer.addEventListener("pointerdown", (event) => {
        const bodyStyles = getComputedStyle(body);
        const SIDEBAR_MIN_WIDTH_STR = bodyStyles.getPropertyValue("--sidebar-min-width");
        const SIDEBAR_MAX_WIDTH_STR = bodyStyles.getPropertyValue("--sidebar-max-width");
        const SIDEBAR_MIN_WIDTH = parseFloat(SIDEBAR_MIN_WIDTH_STR) ?? 0;
        const SIDEBAR_MAX_WIDTH = parseFloat(SIDEBAR_MAX_WIDTH_STR) ?? body.getBoundingClientRect().right;
        const BODY_LEFT_X = body.getBoundingClientRect().left;
        let sidebarWidth;

        event.preventDefault();
        resizer.setPointerCapture(event.pointerId);  // Capture continues even after dragging out the handle.

        const onMove = (event) => {
            body.classList.add("u-no-transition");
            sidebarWidth = Math.min(Math.max(event.clientX - BODY_LEFT_X, SIDEBAR_MIN_WIDTH), SIDEBAR_MAX_WIDTH);
            body.style.setProperty("--sidebar-width", `${sidebarWidth}px`);
        }
        const onUp = () => {
            body.classList.remove("u-no-transition");
            document.removeEventListener("pointermove", onMove);
            document.removeEventListener("pointerup", onUp);
            pywebview.api.storage_set("sidebarWidth", sidebarWidth);
        }
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
    });
}

async function initSidebarToggle() {
    const toggle = document.getElementById("sidebar-toggle");
    if (!toggle) return;

    let sidebarWidth = await pywebview.api.storage_get("sidebarWidth");
    if (sidebarWidth) sidebarWidth += "px";
    let collapsed = await pywebview.api.storage_get("sidebarIsCollapsed") ?? false;

    const toggleSidebar = () => {
        if (collapsed) {
            // `sidebarWidth` will be an empty string if body does not have `--sidebar-width` property.
            sidebarWidth = document.body.style.getPropertyValue("--sidebar-width");
            document.body.style.removeProperty("--sidebar-width");
            toggle.dataset.title = "展开侧边栏";
        } else {
            if (sidebarWidth) document.body.style.setProperty("--sidebar-width", sidebarWidth);
            toggle.dataset.title = "收起侧边栏";
        }
    }
    if (collapsed) document.body.classList.add("is-collapsed");
    toggleSidebar();

    toggle.addEventListener("click", () => {
        collapsed = document.body.classList.toggle("is-collapsed");
        toggleSidebar();
        pywebview.api.storage_set("sidebarIsCollapsed", collapsed);
    });
}

async function initSidebarSectionsToggle() {
    let sidebarEachSectionIsCollapsed = await pywebview.api.storage_get("sidebarEachSectionIsCollapsed");
    if (!sidebarEachSectionIsCollapsed || typeof sidebarEachSectionIsCollapsed !== 'object')
        sidebarEachSectionIsCollapsed = {};

    document.querySelectorAll(".sidebar__main>section>header>button")
        .forEach((toggle) => {
            const section = toggle.parentElement?.parentElement;
            if (section.id && sidebarEachSectionIsCollapsed[section.id]) section.classList.add("is-collapsed");

            toggle.addEventListener("click", () => {
                if (!section) return;
                const collapsed = section.classList.toggle("is-collapsed");
                if (section.id) sidebarEachSectionIsCollapsed[section.id] = collapsed;
                pywebview.api.storage_set("sidebarEachSectionIsCollapsed", sidebarEachSectionIsCollapsed);
            });
        });
}

async function initThemeToggle() {
    const root = document.documentElement;
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    const icons = toggle.querySelectorAll(".icon");
    const themes = ["system", "light", "dark"];
    let themeIndex = await pywebview.api.storage_get("themeIndex") ?? 0;

    const setTheme = (themeIndex) => {
        showIconfromList(icons, themeIndex);
        if (themes[themeIndex] === "system") {
            root.removeAttribute("data-theme");
        } else {
            root.dataset.theme = themes[themeIndex];
        }
    }
    setTheme(themeIndex);

    toggle.addEventListener("click", () => {
        themeIndex = (themeIndex + 1) % icons.length;
        setTheme(themeIndex);
        pywebview.api.storage_set("themeIndex", themeIndex);
    });
}

// The CSS selector `*:hover::-webkit-scrollbar-thumb` does not work properly in pywebview.
function initScrollbarToggle() {
    if (isWebKitGTK) return;
    let scrollContainers = ".sidebar__main, .query__result";
    document.querySelectorAll(scrollContainers).forEach((element) => {
        element.addEventListener("mouseenter", () => element.classList.add("is-scrolling"));
        element.addEventListener("mouseleave", () => element.classList.remove("is-scrolling"));
    });
}

async function displayCurrentSource() {
    const currentSourceElement = document.getElementById("source-current");
    const currentSourceRegName = await pywebview.api.current_source_reg_name();
    const currentSourceName = await pywebview.api.get_source_name(currentSourceRegName);
    currentSourceElement.replaceChildren();  // Clear the previously dispalyed source.
    currentSourceElement.appendChild(document.createTextNode(currentSourceName));
}

async function displayDictSourcesList() {
    const sourcesList = await pywebview.api.list_sources_reg_name();
    const sourcesListElement = document.getElementById("source-list");
    const currentSourceRegName = await pywebview.api.current_source_reg_name();

    let sourceElement, sourceButton;
    let sourceName, sourceNameElement;
    let sourceDescription, sourceDescriptionElement;
    for (const sourceRegName of sourcesList) {
        sourceElement = document.createElement("li");

        sourceButton = document.createElement("button");
        sourceButton.classList.add("u-button-feedback");
        sourceButton.type = "button";
        sourceButton.dataset.source = sourceRegName;
        if (sourceRegName === currentSourceRegName) sourceButton.classList.add("is-selected");
        sourceButton.onclick = () => setSource(sourceRegName);

        sourceName = await pywebview.api.get_source_name(sourceRegName);
        sourceNameElement = document.createElement("strong");
        sourceNameElement.classList.add("source__name");
        sourceNameElement.appendChild(document.createTextNode(sourceName));
        sourceButton.appendChild(sourceNameElement);

        sourceDescription = await pywebview.api.get_source_description(sourceRegName);
        sourceDescriptionElement = document.createElement("small");
        sourceDescriptionElement.classList.add("source__desc");
        sourceDescriptionElement.appendChild(document.createTextNode(sourceDescription));
        sourceButton.appendChild(sourceDescriptionElement);

        sourceElement.appendChild(sourceButton);
        sourcesListElement.appendChild(sourceElement);
    }
}

function setSource(regName) {
    pywebview.api.set_current_source(regName);

    document.querySelectorAll(".source__list button.is-selected")
        .forEach((sourceButton) => sourceButton.classList.remove("is-selected"));
    const currentSourceButton = document.querySelector(`.source__list button[data-source="${regName}"]`);
    if (currentSourceButton) currentSourceButton.classList.add("is-selected");

    displayCurrentSource();
}

function lookup() {
    const word = document.getElementById("query-input").value.trim();
    if (!word) return;

    const button = document.getElementById("query-button");
    button.disabled = true;  // Remember to enable the button.

    const pageElement = document.getElementById("query-result");
    pageElement.replaceChildren();  // Clear the previous query results.
    pageElement.classList.remove("error");

    pywebview.api.lookup(word)
        .then((response) => {
            console.debug("[lookup]", word, "->", response);
            assemblePage(response, pageElement);
        })
        .catch((error) => {
            console.error("[lookup] failed:", word, error);
            assembleErrorPage(error, word, pageElement);
        })
        .finally(() => button.disabled = false);
}

function assemblePage(pageMeta, pageElement) {
    if (!pageMeta || typeof pageMeta !== "object" || pageMeta.is_error === undefined)
        console.error("[assemblePage] unknown pageMeta:", pageMeta);

    pageElement.classList.remove("is-error");
    if (pageMeta.is_error) pageElement.classList.add("is-error");  // Handle the error thrown by dictionary source.

    const titleElement = document.createElement("h1");
    titleElement.appendChild(document.createTextNode(pageMeta.word));
    pageElement.appendChild(titleElement);

    for (const section of pageMeta.sections) {
        pageElement.appendChild(assembleSection(section));
    }
}

// Handle the error thrown by `pywebview.api.lookup()`.
function assembleErrorPage(error, word, pageElement) {
    pageElement.replaceChildren();
    pageElement.classList.add("is-error");

    const titleElement = document.createElement("h1");
    titleElement.appendChild(document.createTextNode(word));
    pageElement.appendChild(titleElement);

    const sectionElement = document.createElement("section");

    const subtitleElement = document.createElement("h2");
    subtitleElement.appendChild(document.createTextNode("错误"));
    sectionElement.appendChild(subtitleElement);

    const listElement = document.createElement("ul");
    const itemElement = document.createElement("li");
    assembleText(itemElement, String(error));
    listElement.appendChild(itemElement);
    sectionElement.appendChild(listElement);

    pageElement.appendChild(sectionElement);
}

function assembleSection(sectionMeta) {
    const sectionElement = document.createElement("section");

    const titleElement = document.createElement("h2");
    titleElement.appendChild(document.createTextNode(sectionMeta.title));
    sectionElement.appendChild(titleElement);

    const listElement = document.createElement("ul");
    for (const item of sectionMeta.items) {
        listElement.appendChild(assembleItem(item));
    }
    sectionElement.appendChild(listElement);

    return sectionElement;
}

function assembleItem(itemMeta) {
    const itemElement = document.createElement("li");
    switch (itemMeta.type) {
        case "text":
            assembleText(itemElement, itemMeta.text, itemMeta.font_style);
            break;
        case "phonetic":
            assemblePhonetic(itemElement, itemMeta.phonetic, itemMeta.name, itemMeta.audio_url);
            break;
        case "link":
            assembleLink(itemElement, itemMeta.text, itemMeta.url);
            break;
        default:
            itemElement.classList.add("error");
            assembleText(itemElement, "Unknown type: " + JSON.stringify(itemMeta));
            break;
    }
    return itemElement;
}

function assembleText(itemElement, text, fontStyle = "normal") {
    itemElement.classList.add("text");
    itemElement.classList.add(fontStyle);
    itemElement.appendChild(document.createTextNode(text));
}

function assemblePhonetic(itemElement, phonetic, name, audioUrl) {
    itemElement.classList.add("phonetic");
    const text = name ? `${name} ${phonetic}` : `${phonetic}`;
    itemElement.appendChild(document.createTextNode(text));

    const playButton = document.createElement("button");
    playButton.disabled = true;
    playButton.classList.add("phonetic__player");
    playButton.type = "button";
    playButton.innerHTML = PLAY_ICONS_DOM;

    if (!audioUrl) return;
    const audio = new Audio();
    audio.oncanplay = () => playButton.disabled = false;
    audio.onerror = () => console.warn("Cannot play the audio:", audioUrl);
    audio.src = audioUrl;
    const icons = playButton.querySelectorAll(".icon");

    let waveTimer;
    const startWave = () => {
        let i = -1;  // Show icons starting from `volume0`.
        waveTimer = setInterval(() => {
            i = (i + 1) % (icons.length - 1);  // Exclude `volume-1` icon.
            showIconfromList(icons, i);
        }, 300);
    }
    const stopWave = () => {
        clearInterval(waveTimer);
        waveTimer = null;
        showIconfromList(icons, 2);
    }

    audio.onplay = startWave;
    audio.onpause = stopWave;
    audio.onended = stopWave;
    audio.onerror = stopWave;

    playButton.onclick = () => {
        if (audio.paused) { audio.play(); }
        else { audio.pause(); audio.currentTime = 0; }  // Start from the beginning after pause.
    };
    itemElement.appendChild(playButton);
}

function assembleLink(itemElement, text, url) {
    itemElement.classList.add("link");
    const linkElement = document.createElement("a");
    linkElement.href = url;
    linkElement.title = "使用默认浏览器打开：" + url;
    linkElement.target = "_blank";  // Open via default browser.
    linkElement.rel = "noopener noreferrer";
    linkElement.appendChild(document.createTextNode(text));
    itemElement.appendChild(linkElement);
}

function showIconfromList(icons, i) {
    icons.forEach((icon, j) => icon.style.display = (j === i ? "block" : "none"));
}