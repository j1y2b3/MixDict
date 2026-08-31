window.addEventListener("pywebviewready", initApp);
function initApp() {
    displayCurrentSource();
    displayDictSourcesList();
    document.getElementById("query-input").focus();
}

// The CSS selector `*:hover::-webkit-scrollbar-thumb` does not work properly in pywebview.
function initScrollbarToggle() {
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

    let sourceElement, sourceButton;
    let sourceName, sourceNameElement;
    let sourceDescription, sourceDescriptionElement;
    for (const sourceRegName of sourcesList) {
        sourceElement = document.createElement("li");

        sourceButton = document.createElement("button");
        sourceButton.classList.add("u-button-feedback");
        sourceButton.type = "button";
        sourceButton.onclick = () => setSource(sourceRegName);

        sourceName = await pywebview.api.get_source_name(sourceRegName);
        sourceNameElement = document.createElement("strong");
        sourceNameElement.classList.add("source-name");
        sourceNameElement.appendChild(document.createTextNode(sourceName));
        sourceButton.appendChild(sourceNameElement);

        sourceDescription = await pywebview.api.get_source_description(sourceRegName);
        sourceDescriptionElement = document.createElement("small");
        sourceDescriptionElement.classList.add("source-desc");
        sourceDescriptionElement.appendChild(document.createTextNode(sourceDescription));
        sourceButton.appendChild(sourceDescriptionElement);

        sourceElement.appendChild(sourceButton);
        sourcesListElement.appendChild(sourceElement);
    }
}

async function setSource(regName) {
    await pywebview.api.set_source(regName);
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
        .then(response => assemblePage(response, pageElement))
        .catch(error => assembleErrorPage(error, word, pageElement))
        .finally(() => button.disabled = false);
}

function assemblePage(pageMeta, pageElement) {
    if (pageMeta.is_error) pageElement.classList.add("error");  // Handle the error thrown by dictionary source.

    const titleElement = document.createElement("h1");
    titleElement.appendChild(document.createTextNode(pageMeta.word));
    pageElement.appendChild(titleElement);

    for (const section of pageMeta.sections) {
        pageElement.appendChild(assembleSection(section));
    }
}

// Handle the error thrown by `pywebview.api.lookup()`.
function assembleErrorPage(error, word, pageElement) {
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
            assembleText(itemElement, itemMeta.text, itemMeta.font_size);
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

function assembleText(itemElement, text, fontSize) {
    itemElement.classList.add("text");
    itemElement.classList.add(fontSize);
    itemElement.appendChild(document.createTextNode(text));
}

function assemblePhonetic(itemElement, phonetic, name, audioUrl) {
    itemElement.classList.add("phonetic");
    const text = name ? `${name} ${phonetic}` : `${phonetic}`;
    itemElement.appendChild(document.createTextNode(text));

    const displayPlayButton = (itemElement, audio) => {
        const playButton = document.createElement("button");
        playButton.type = "button";
        playButton.appendChild(document.createTextNode("🔊"));
        playButton.onclick = () => audio.play();
        itemElement.appendChild(playButton);
    }

    if (!audioUrl) return;
    const audio = new Audio();
    audio.oncanplay = () => displayPlayButton(itemElement, audio);
    audio.onerror = () => console.warn("Cannot play the audio:", audioUrl);
    audio.src = audioUrl;
}

function assembleLink(itemElement, text, url) {
    itemElement.classList.add("link");
    const linkElement = document.createElement("a");
    linkElement.href = url;
    linkElement.target = "_blank";  // Open via default browser.
    linkElement.rel = "noopener noreferrer";
    linkElement.appendChild(document.createTextNode(text));
    itemElement.appendChild(linkElement);
}