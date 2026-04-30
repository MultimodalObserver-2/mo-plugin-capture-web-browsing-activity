from dataclasses import dataclass, asdict
CSV_HEADERS: dict[str, list[str]] = {
    "keystrokes":  ["browser", "pageUrl", "pageTitle", "keyValue", "captureTimestamp"],
    "mouseClicks": ["browser", "pageUrl", "pageTitle", "xPage", "yPage",
                    "xClient", "yClient", "xScreen", "yScreen", "button", "captureTimestamp"],
    "mouseMoves":  ["browser", "pageUrl", "pageTitle", "xPage", "yPage",
                    "xClient", "yClient", "xScreen", "yScreen",
                    "xMovement", "yMovement", "captureTimestamp"],
    "mouseUps":    ["browser", "pageUrl", "pageTitle", "selectedText", "captureTimestamp"],
    "searchs":     ["browser", "pageUrl", "pageTitle", "search", "captureTimestamp"],
    "tabs":        ["browser", "tabUrl", "tabTitle", "actionType",
                    "tabIndex", "tabId", "windowId", "captureTimestamp"],
}


def get_str(payload: dict, key: str) -> str:
    return str(payload.get(key, "") or "")


def get_int(payload: dict, key: str) -> int:
    try:
        return int(payload.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0


@dataclass
class Keystroke:
    browser: str = ""
    pageUrl: str = ""
    pageTitle: str = ""
    keyValue: str = ""
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "keystrokes"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        return sep.join([
            self.browser, self.pageUrl, self.pageTitle,
            self.keyValue, str(self.captureTimestamp),
        ])


@dataclass
class MouseClick:
    browser: str = ""
    pageUrl: str = ""
    pageTitle: str = ""
    xPage: int = 0
    yPage: int = 0
    xClient: int = 0
    yClient: int = 0
    xScreen: int = 0
    yScreen: int = 0
    button: int = 0
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "mouseClicks"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        return sep.join(str(v) for v in [
            self.browser, self.pageUrl, self.pageTitle,
            self.xPage, self.yPage, self.xClient, self.yClient,
            self.xScreen, self.yScreen, self.button, self.captureTimestamp,
        ])


@dataclass
class MouseMove:
    browser: str = ""
    pageUrl: str = ""
    pageTitle: str = ""
    xPage: int = 0
    yPage: int = 0
    xClient: int = 0
    yClient: int = 0
    xScreen: int = 0
    yScreen: int = 0
    xMovement: int = 0
    yMovement: int = 0
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "mouseMoves"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        return sep.join(str(v) for v in [
            self.browser, self.pageUrl, self.pageTitle,
            self.xPage, self.yPage, self.xClient, self.yClient,
            self.xScreen, self.yScreen,
            self.xMovement, self.yMovement,
            self.captureTimestamp,
        ])


@dataclass
class MouseUp:
    browser: str = ""
    pageUrl: str = ""
    pageTitle: str = ""
    selectedText: str = ""
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "mouseUps"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        selected = self.selectedText
        if sep in selected or '"' in selected or "\n" in selected:
            selected = '"' + selected.replace('"', '""') + '"'
        return sep.join([
            self.browser, self.pageUrl, self.pageTitle,
            selected, str(self.captureTimestamp),
        ])


@dataclass
class SearchAction:
    browser: str = ""
    pageUrl: str = ""
    pageTitle: str = ""
    search: str = ""
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "searchs"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        return sep.join([
            self.browser, self.pageUrl, self.pageTitle,
            self.search, str(self.captureTimestamp),
        ])


@dataclass
class TabAction:
    browser: str = ""
    tabUrl: str = ""
    tabTitle: str = ""
    actionType: str = ""
    tabIndex: int = 0
    tabId: int = 0
    windowId: int = 0
    captureTimestamp: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = "tabs"
        return d

    def to_csv_row(self, sep: str = ",") -> str:
        return sep.join(str(v) for v in [
            self.browser, self.tabUrl, self.tabTitle, self.actionType,
            self.tabIndex, self.tabId, self.windowId, self.captureTimestamp,
        ])


def parse_event(path: str, payload: dict, timestamp: float) -> dict | None:
    if path == "/keystrokes":
        return Keystroke(
            browser=get_str(payload, "browser"),
            pageUrl=get_str(payload, "pageUrl"),
            pageTitle=get_str(payload, "pageTitle"),
            keyValue=get_str(payload, "keyValue"),
            captureTimestamp=timestamp,
        ).to_dict()

    if path == "/mouseClicks":
        return MouseClick(
            browser=get_str(payload, "browser"),
            pageUrl=get_str(payload, "pageUrl"),
            pageTitle=get_str(payload, "pageTitle"),
            xPage=get_int(payload, "xPage"),
            yPage=get_int(payload, "yPage"),
            xClient=get_int(payload, "xClient"),
            yClient=get_int(payload, "yClient"),
            xScreen=get_int(payload, "xScreen"),
            yScreen=get_int(payload, "yScreen"),
            button=get_int(payload, "button"),
            captureTimestamp=timestamp,
        ).to_dict()

    if path == "/mouseMoves":
        return MouseMove(
            browser=get_str(payload, "browser"),
            pageUrl=get_str(payload, "pageUrl"),
            pageTitle=get_str(payload, "pageTitle"),
            xPage=get_int(payload, "xPage"),
            yPage=get_int(payload, "yPage"),
            xClient=get_int(payload, "xClient"),
            yClient=get_int(payload, "yClient"),
            xScreen=get_int(payload, "xScreen"),
            yScreen=get_int(payload, "yScreen"),
            xMovement=get_int(payload, "xMovement"),
            yMovement=get_int(payload, "yMovement"),
            captureTimestamp=timestamp,
        ).to_dict()

    if path == "/mouseUps":
        return MouseUp(
            browser=get_str(payload, "browser"),
            pageUrl=get_str(payload, "pageUrl"),
            pageTitle=get_str(payload, "pageTitle"),
            selectedText=get_str(payload, "selectedText"),
            captureTimestamp=timestamp,
        ).to_dict()

    if path == "/searchs":
        return SearchAction(
            browser=get_str(payload, "browser"),
            pageUrl=get_str(payload, "pageUrl"),
            pageTitle=get_str(payload, "pageTitle"),
            search=get_str(payload, "search"),
            captureTimestamp=timestamp,
        ).to_dict()

    if path == "/tabs":
        return TabAction(
            browser=get_str(payload, "browser"),
            tabUrl=get_str(payload, "tabUrl"),
            tabTitle=get_str(payload, "tabTitle"),
            actionType=get_str(payload, "actionType"),
            tabIndex=get_int(payload, "tabIndex"),
            tabId=get_int(payload, "tabId"),
            windowId=get_int(payload, "windowId"),
            captureTimestamp=timestamp,
        ).to_dict()

    return None
