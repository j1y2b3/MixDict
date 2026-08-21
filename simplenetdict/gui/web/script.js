window.addEventListener("pywebviewready", initApp);
function initApp() {
    displayCurrentSource();
    displayDictSourcesList();
}

async function displayCurrentSource() {
    const currentSourceElement = document.getElementById("cur-source");
    const currentSourceRegName = await pywebview.api.current_source_reg_name();
    const currentSourceName = await pywebview.api.get_source_name(currentSourceRegName);
    currentSourceElement.appendChild(document.createTextNode(currentSourceName));
}

async function displayDictSourcesList() {
    const sourcesList = await pywebview.api.list_sources_reg_name();
    const sourcesListElement = document.getElementById("sources-list");

    let sourceElement, sourceName;
    for (const sourceRegName of sourcesList) {
        sourceElement = document.createElement("li");

        sourceName = await pywebview.api.get_source_name(sourceRegName);
        const sourceNameElement = document.createElement("span");
        sourceNameElement.className = "source-name";
        sourceNameElement.appendChild(document.createTextNode(sourceName));
        sourceElement.appendChild(sourceNameElement);

        sourceDescription = await pywebview.api.get_source_description(sourceRegName);
        const sourceDescriptionElement = document.createElement("span");
        sourceDescriptionElement.className = "source-desc";
        sourceDescriptionElement.appendChild(document.createTextNode(sourceDescription));
        sourceElement.appendChild(sourceDescriptionElement);

        sourcesListElement.appendChild(sourceElement);
    }
}

function lookup() {
    const word = document.getElementById("query-box").value.trim();
    if (!word) return;

    const button = document.getElementById("query-btn");
    button.disabled = true;  // Remember to enable the button.

    const pageElement = document.getElementById("result");
    pageElement.replaceChildren();  // Clear the previous query results.

    pywebview.api.lookup(word)
        .then(response => assemblePage(response, pageElement))
        .catch(error => assembleErrorPage(error, word, pageElement))
        .finally(() => button.disabled = false);
}

function assemblePage(pageMeta, pageElement) {
    const titleElement = document.createElement("h1");
    titleElement.appendChild(document.createTextNode(pageMeta.word));
    pageElement.appendChild(titleElement);

    for (const section of pageMeta.sections) {
        pageElement.appendChild(assembleSection(section));
    }
}

function assembleErrorPage(error, word, pageElement) {
    const titleElement = document.createElement("h1");
    titleElement.appendChild(document.createTextNode(word));
    pageElement.appendChild(titleElement);

    const sectionElement = document.createElement("section");

    const subtitleElement = document.createElement("h2");
    subtitleElement.appendChild(document.createTextNode("错误"));
    sectionElement.appendChild(subtitleElement);

    const listElement = document.createElement("ul");
    listElement.appendChild(assembleText(String(error), true));
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
    switch (itemMeta.type) {
        case "text":
            return assembleText(itemMeta.text);
        case "phonetic":
            return assemblePhonetic(itemMeta.name, itemMeta.phonetic, itemMeta.audio_url);
        default:
            return assembleText("Unknown type: " + JSON.stringify(itemMeta), true);
    }
}

function assembleText(text, isError = false) {
    const itemElement = document.createElement("li");
    if (isError) {
        itemElement.className = "error";
    } else {
        itemElement.className = "text";
    }
    itemElement.appendChild(document.createTextNode(text));
    return itemElement;
}

function assemblePhonetic(name, phonetic, audioUrl) {
    const itemElement = document.createElement("li");
    itemElement.className = "phonetic";
    itemElement.appendChild(document.createTextNode(`${name} ${phonetic}`));

    if (audioUrl) {
        const playButton = document.createElement("button");
        playButton.appendChild(document.createTextNode("🔊"));
        playButton.onclick = () => new Audio(audioUrl).play();
        itemElement.appendChild(playButton);
    }

    return itemElement;
}