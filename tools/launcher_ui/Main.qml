import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root
    width: 1100
    height: 760
    minimumWidth: 900
    minimumHeight: 620
    visible: true
    title: "Sims 4 Multiplayer"
    color: Theme.cBg
    font.family: Theme.fFont

    function _escapeHtml(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;") }
    property int navIndex: 0
    property int qmlLineCount: 0
    property int logLineCount: 0

    onClosing: bridge.shutdown()

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ==================================================== sidebar (60px rail)
        Rectangle {
            Layout.preferredWidth: 60
            Layout.fillHeight: true
            color: Theme.cBgDeep

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 20
                anchors.bottomMargin: 20
                spacing: 0

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    Layout.bottomMargin: 24
                    radius: 10
                    color: Theme.cAccent
                    Text {
                        anchors.centerIn: parent
                        text: "S4"
                        color: "#ffffff"
                        font.family: Theme.fFont
                        font.pixelSize: 13
                        font.bold: true
                    }
                }

                Repeater {
                    model: [
                        { icon: "\u25b6", index: 0 },
                        { icon: "\u2699", index: 1 },
                        { icon: "\u2630", index: 2 },
                        { icon: "\u2695", index: 3 }
                    ]
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        property bool active: navIndex === modelData.index
                        Rectangle {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: 3
                            height: 26
                            radius: 1.5
                            color: parent.active ? Theme.cAccent : "transparent"
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 40
                            height: 40
                            radius: 10
                            color: parent.active ? Qt.rgba(255, 255, 255, 0.08) : (ma.containsMouse ? Qt.rgba(255, 255, 255, 0.05) : "transparent")
                        }
                        Text {
                            anchors.centerIn: parent
                            text: modelData.icon
                            color: parent.active ? Theme.cFg : Theme.cMuted
                            font.pixelSize: (modelData.index === 0 ? 14 : 16)
                        }
                        MouseArea {
                            id: ma
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: navIndex = modelData.index
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredHeight: 18
                    Layout.preferredWidth: 34
                    radius: 9
                    color: Qt.rgba(255, 255, 255, 0.06)
                    visible: bridge.playerCount > 0
                    Text {
                        anchors.centerIn: parent
                        text: "\u25cf " + bridge.playerCount
                        color: Theme.cGreen
                        font.family: Theme.fFont
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
            }
        }

        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: Theme.cBorder }

        // ==================================================== content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: navIndex

            // ------------------------------------------------ page 0: play
            ScrollView {
                id: playPage
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    x: 32
                    width: playPage.width - 64
                    spacing: 20

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 32
                        spacing: 4
                        Text {
                            text: "Play on LAN"
                            color: Theme.cFg
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Text {
                            text: "Host a new game or join your friends\u2019 session"
                            color: Theme.cMuted
                            font.pixelSize: 12
                        }
                    }

// two equal cards
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        // ---- HOST GAME
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 400
                            color: Theme.cPane
                            radius: 10
                            border.width: 1
                            border.color: Theme.cBorder
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 24
                                spacing: 14

                                Text {
                                    text: "HOST GAME"
                                    color: Theme.cFg
                                    font.pixelSize: 13
                                    font.bold: true
                                    font.letterSpacing: 1.2
                                }
                                Text {
                                    text: "Select the save game you would like to play with."
                                    color: Theme.cMuted
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Item { Layout.preferredHeight: 4 }

                                ColumnLayout { Layout.fillWidth: true; spacing: 6
                                    Text { text: "YOUR NAME"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                    AppTextField { Layout.fillWidth: true; text: bridge.hostName; placeholderText: "Enter player name"; onTextChanged: bridge.hostName = text }
                                }
                                ColumnLayout { Layout.fillWidth: true; spacing: 6
                                    Text { text: "SAVE GAME"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                    RowLayout { Layout.fillWidth: true; spacing: 8
                                        AppComboBox {
                                            id: saveCombo
                                            Layout.fillWidth: true
                                            model: bridge.saves
                                            enabled: bridge.saves.length > 0
                                            onCurrentIndexChanged: bridge.selectSave(currentIndex)
                                        }
                                        AppButton {
                                            text: "Browse"
                                            implicitWidth: 84
                                            onClicked: bridge.refreshSaves()
                                        }
                                    }
                                }

                                Item { Layout.fillHeight: true }

                                AppButton {
                                    text: bridge.lobbyRunning ? "Hosting..." : "Host Game"
                                    Layout.fillWidth: true
                                    bgColor: Theme.cAccent
                                    bgHover: Theme.cAccentHover
                                    enabled: !bridge.lobbyRunning
                                    onClicked: bridge.startLobby()
                                }
                            }
                        }

// ---- JOIN GAME
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 400
                            color: Theme.cPane
                            radius: 10
                            border.width: 1
                            border.color: Theme.cBorder
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 24
                                spacing: 14

                                Text {
                                    text: "JOIN GAME"
                                    color: Theme.cFg
                                    font.pixelSize: 13
                                    font.bold: true
                                    font.letterSpacing: 1.2
                                }
                                Text {
                                    text: "Join an existing game using the server IP address."
                                    color: Theme.cMuted
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Item { Layout.preferredHeight: 4 }

                                ColumnLayout { Layout.fillWidth: true; spacing: 6
                                    Text { text: "SERVER IP ADDRESS"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                    AppTextField { Layout.fillWidth: true; text: bridge.joinIp; placeholderText: "Enter IP address here"; onTextChanged: bridge.joinIp = text }
                                }
                                ColumnLayout { Layout.fillWidth: true; spacing: 6
                                    Text { text: "YOUR NAME"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                    AppTextField { Layout.fillWidth: true; text: bridge.joinName; placeholderText: "Enter player name"; onTextChanged: bridge.joinName = text }
                                }
                                ColumnLayout { Layout.fillWidth: true; spacing: 6
                                    Text { text: "PORT"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                    AppTextField { Layout.fillWidth: true; text: bridge.joinPort; placeholderText: "8765"; onTextChanged: bridge.joinPort = text }
                                }

                                Item { Layout.fillHeight: true }

                                AppButton {
                                    text: bridge.joining ? "Joining..." : "Join Game"
                                    Layout.fillWidth: true
                                    bgColor: Theme.cAccent
                                    bgHover: Theme.cAccentHover
                                    enabled: !bridge.joining
                                    onClicked: bridge.joinLobby()
                                }
                            }
                        }
                    }

                    // status panel
                    Rectangle {
                        Layout.fillWidth: true
                        visible: bridge.lobbyRunning || bridge.joining || bridge.canJoinStart
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: statusCol.implicitHeight + 32
                        ColumnLayout {
                            id: statusCol
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            StatusCard { id: lobbyCard; Layout.fillWidth: true; visible: bridge.lobbyRunning }
                            StatusCard { id: shareCard; Layout.fillWidth: true; visible: bridge.lobbyRunning && bridge.canShare && shareCard.cardPhase !== "" }
                            StatusCard { id: joinCard; Layout.fillWidth: true; visible: bridge.joining }

                            RowLayout {
                                Layout.fillWidth: true
                                visible: bridge.lobbyRunning
                                spacing: 8
                                Text { text: "LAN IP"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                AppComboBox {
                                    id: lanIpCombo
                                    Layout.preferredWidth: 240
                                    model: bridge.lanIps
                                    Component.onCompleted: currentIndex = bridge.lanIpIndex
                                    onCurrentIndexChanged: bridge.lanIpSelected(currentIndex)
                                }
                                AppButton { text: "Copy"; implicitWidth: 64; onClicked: bridge.copyIp() }
                                Item { Layout.fillWidth: true }
                                AppButton { text: "Share Save"; fgColor: Theme.cAccent; enabled: bridge.canShare; onClicked: bridge.shareSave() }
                                AppButton { text: "Start Game"; bgColor: Theme.cGreen; bgHover: Qt.lighter(Theme.cGreen, 1.1); enabled: bridge.canHostStart; onClicked: bridge.startGameHost() }
                                AppButton { text: "Stop"; fgColor: Theme.cRed; onClicked: bridge.stopLobby() }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                visible: bridge.canJoinStart
                                spacing: 8
                                Text { text: "Connected to server"; color: Theme.cMuted; font.pixelSize: 11 }
                                Item { Layout.fillWidth: true }
                                AppButton { text: "Start Game"; bgColor: Theme.cGreen; bgHover: Qt.lighter(Theme.cGreen, 1.1); onClicked: bridge.startGameJoin() }
                            }
                        }
                    }

                    Item { Layout.preferredHeight: 32 }
                }
            }

            // ------------------------------------------------ page 1: settings
            ScrollView {
                id: settingsPage
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    x: 32
                    width: settingsPage.width - 64
                    spacing: 20

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 32
                        spacing: 4
                        Text {
                            text: "Settings"
                            color: Theme.cFg
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Text {
                            text: "Set up the required The Sims 4 file and folder paths."
                            color: Theme.cMuted
                            font.pixelSize: 12
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: settingsCol.implicitHeight + 48
                        ColumnLayout {
                            id: settingsCol
                            anchors.fill: parent
                            anchors.margins: 24
                            spacing: 16

                            ColumnLayout { Layout.fillWidth: true; spacing: 6
                                Text { text: "THE SIMS 4 GAME"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                RowLayout { Layout.fillWidth: true; spacing: 8
                                    AppTextField { id: fieldGame; Layout.fillWidth: true; text: bridge.gamePath; placeholderText: "Path to TS4_x64.exe"; onTextChanged: bridge.gamePath = text }
                                    AppButton { text: "Browse"; implicitWidth: 84; onClicked: bridge.browse("game") }
                                }
                            }
                            ColumnLayout { Layout.fillWidth: true; spacing: 6
                                Text { text: "MODS FOLDER"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                RowLayout { Layout.fillWidth: true; spacing: 8
                                    AppTextField { id: fieldMods; Layout.fillWidth: true; text: bridge.modsPath; placeholderText: "Documents\\Electronic Arts\\The Sims 4\\Mods"; onTextChanged: bridge.modsPath = text }
                                    AppButton { text: "Browse"; implicitWidth: 84; onClicked: bridge.browse("mods") }
                                }
                            }
                            ColumnLayout { Layout.fillWidth: true; spacing: 6
                                Text { text: "DOCUMENTS"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                RowLayout { Layout.fillWidth: true; spacing: 8
                                    AppTextField { id: fieldSaves; Layout.fillWidth: true; text: bridge.savesPath; placeholderText: "Documents\\Electronic Arts\\The Sims 4"; onTextChanged: bridge.savesPath = text }
                                    AppButton { text: "Browse"; implicitWidth: 84; onClicked: bridge.browse("saves") }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.cBorder }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                AppButton { text: "Install Mod"; bgColor: Theme.cAccent; bgHover: Theme.cAccentHover; onClicked: bridge.installMod() }
                                AppButton { text: "Check Updates"; onClicked: bridge.checkUpdates() }
                                Item { Layout.fillWidth: true }
                                Text { text: "Auto-update"; color: Theme.cFg; font.pixelSize: 11 }
                                Switch {
                                    id: autoSwitch
                                    checked: bridge.autoUpdate
                                    onToggled: bridge.autoUpdate = checked
                                    implicitWidth: 44
                                    implicitHeight: 24
                                    indicator: Rectangle {
                                        y: (autoSwitch.height - height) / 2
                                        x: autoSwitch.checked ? autoSwitch.width - width - 3 : 3
                                        width: 18
                                        height: 18
                                        radius: 9
                                        color: autoSwitch.checked ? "#ffffff" : Theme.cMuted
                                        Behavior on x { NumberAnimation { duration: 150 } }
                                    }
                                    background: Rectangle {
                                        implicitHeight: 24
                                        implicitWidth: 44
                                        radius: 12
                                        color: autoSwitch.checked ? Theme.cAccent : "#2a2e3a"
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }
                                }
                            }

                            Text { id: setupStatus; Layout.fillWidth: true; font.pixelSize: 11; font.family: Theme.fMono; color: Theme.cMuted; wrapMode: Text.Wrap }
                            Text { id: updateStatus; Layout.fillWidth: true; font.pixelSize: 11; font.family: Theme.fMono; color: Theme.cMuted; wrapMode: Text.Wrap }
                        }
                    }

                    Item { Layout.preferredHeight: 32 }
                }
            }

            // ------------------------------------------- page 2: diagnostics
            ScrollView {
                id: diagPage
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    x: 32
                    width: diagPage.width - 64
                    spacing: 20

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 32
                        spacing: 4
                        Text {
                            text: "Diagnostics"
                            color: Theme.cFg
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Text {
                            text: "Collect every log into one file, or send it straight to the other PC."
                            color: Theme.cMuted
                            font.pixelSize: 12
                        }
                    }

                    // ---- status summary
                    Rectangle {
                        Layout.fillWidth: true
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: summaryCol.implicitHeight + 40
                        ColumnLayout {
                            id: summaryCol
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "RUNTIME VERSION"; color: Theme.cMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
                                Item { Layout.fillWidth: true }
                                Text { text: bridge.runtimeVersion; color: Theme.cFg; font.family: Theme.fMono; font.pixelSize: 11 }
                            }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.cBorder }
                            Text {
                                Layout.fillWidth: true
                                text: bridge.diagStatus !== "" ? bridge.diagStatus : "Collecting status..."
                                color: Theme.cMuted
                                font.family: Theme.fMono
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    // ---- actions
                    Rectangle {
                        Layout.fillWidth: true
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: actionsCol.implicitHeight + 40
                        ColumnLayout {
                            id: actionsCol
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                AppButton {
                                    text: "Export diagnostics (.zip)"
                                    bgColor: Theme.cAccent
                                    bgHover: Theme.cAccentHover
                                    onClicked: bridge.exportDiagnostics()
                                }
                                AppButton {
                                    text: "Send to host"
                                    fgColor: Theme.cGreen
                                    enabled: bridge.diagTarget !== ""
                                    onClicked: bridge.sendDiagnosticsToHost()
                                }
                                AppButton { text: "Open folder"; onClicked: bridge.openDiagnosticsFolder() }
                                Item { Layout.fillWidth: true }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: bridge.diagTarget !== ""
                                      ? ("'Send to host' posts this PC's bundle to " + bridge.diagTarget + " - the host launcher listens there while its lobby is open, and pops the folder open when it arrives.")
                                      : "To send straight to the host: enter their IP address on the Play page (Join side), then press 'Send to host'."
                                color: Theme.cMuted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    // ---- what gets collected
                    Rectangle {
                        Layout.fillWidth: true
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: whatCol.implicitHeight + 40
                        ColumnLayout {
                            id: whatCol
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 10
                            SectionHeader { label: "WHAT GOES IN THE BUNDLE" }
                            Text {
                                Layout.fillWidth: true
                                color: Theme.cMuted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                lineHeight: 1.35
                                text: "\u2022 server log + live server status (host PC)\n" +
                                      "\u2022 the in-game mod log from this PC (the main file - now timestamped)\n" +
                                      "\u2022 the mp.diag dump, the auto-connect config and launcher settings\n" +
                                      "\u2022 this launcher's activity history and version/paths summary\n\n" +
                                      "The identity file is reduced to a hash, and every file is size-capped, so a run-away log can never break the bundle."
                            }
                        }
                    }

                    // ---- host side hint
                    Rectangle {
                        Layout.fillWidth: true
                        color: Theme.cPane
                        radius: 10
                        border.width: 1
                        border.color: Theme.cBorder
                        implicitHeight: hostCol.implicitHeight + 40
                        ColumnLayout {
                            id: hostCol
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 10
                            SectionHeader { label: "HOSTING?" }
                            Text {
                                Layout.fillWidth: true
                                color: Theme.cMuted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                lineHeight: 1.35
                                text: "While your lobby is open, the other player's launcher can post their logs here in one click. " +
                                      "Incoming bundles land in the received folder (this button opens it) and are announced in the log."
                            }
                        }
                    }

                    Item { Layout.preferredHeight: 32 }
                }
            }

            // ------------------------------------------------ page 3: log
            ColumnLayout {
                x: 32
                width: root.width - 60 - 64
                spacing: 20

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 32
                    spacing: 4
                    Text {
                        text: "Activity Log"
                        color: Theme.cFg
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        text: "Live output from the lobby server and launcher."
                        color: Theme.cMuted
                        font.pixelSize: 12
                    }
                }

                // ---- launcher & server log
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.bottomMargin: 8
                    spacing: 6

                    Text {
                        text: "Launcher & Server"
                        color: Theme.cMuted
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 0.8
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: Theme.cBgDeep
                        radius: 8
                        border.width: 1
                        border.color: Theme.cBorder

                        Flickable {
                            id: logFlick
                            anchors.fill: parent
                            anchors.margins: 12
                            clip: true
                            contentHeight: logTextEdit.height
                            flickableDirection: Flickable.VerticalFlick
                            ScrollBar.vertical: ScrollBar {
                                policy: ScrollBar.AsNeeded
                            }
                            TextEdit {
                                id: logTextEdit
                                width: logFlick.width
                                color: Theme.cFg
                                font.family: Theme.fMono
                                font.pixelSize: 11
                                wrapMode: TextEdit.Wrap
                                readOnly: true
                                selectByMouse: true
                                selectByKeyboard: true
                                selectionColor: Theme.cAccent
                                selectedTextColor: "#ffffff"
                                textFormat: Text.RichText
                            }
                        }
                    }
                }

                // ---- QML warnings & errors
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.bottomMargin: 32
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: "QML Warnings"
                            color: Theme.cMuted
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 0.8
                        }
                        Text {
                            text: qmlLineCount === 0 ? "No QML warnings (clean load)."
                                                       : (qmlLineCount + " warning(s).")
                            color: qmlLineCount === 0 ? Theme.cGreen : Theme.cAmber
                            font.pixelSize: 11
                        }
                        Item { Layout.fillWidth: true }
                        AppButton {
                            text: "Clear QML"
                            implicitWidth: 80
                            implicitHeight: 26
                            font.pixelSize: 10
                            visible: qmlLineCount > 0
                            onClicked: { qmlTextEdit.clear(); qmlLineCount = 0 }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: Theme.cBgDeep
                        radius: 8
                        border.width: 1
                        border.color: Theme.cBorder

                        Flickable {
                            id: qmlFlick
                            anchors.fill: parent
                            anchors.margins: 12
                            clip: true
                            contentHeight: qmlTextEdit.height
                            flickableDirection: Flickable.VerticalFlick
                            ScrollBar.vertical: ScrollBar {
                                policy: ScrollBar.AsNeeded
                            }
                            TextEdit {
                                id: qmlTextEdit
                                width: qmlFlick.width
                                color: Theme.cAmber
                                font.family: Theme.fMono
                                font.pixelSize: 11
                                wrapMode: TextEdit.Wrap
                                readOnly: true
                                selectByMouse: true
                                selectByKeyboard: true
                                selectionColor: Theme.cAccent
                                selectedTextColor: "#ffffff"
                                textFormat: Text.RichText
                            }
                        }
                    }
}
            }
        }
    }

    // ========================================================== bridge glue
    Connections {
        target: bridge
        function onLogAppended(line, kind) {
            var escaped = _escapeHtml(line)
            if (kind === "qml") {
                qmlTextEdit.append("<span style='color:#ffab40'>" + escaped + "</span>")
                qmlLineCount++
            } else {
                var c = kind === "error" ? "#ff5252" : (kind === "muted" ? "#8a94a6" : "#eceff4")
                logTextEdit.append("<span style='color:" + c + "'>" + escaped + "</span>")
                logLineCount++
            }
        }
        function onSetupStatusChanged(text, color) { setupStatus.text = text; setupStatus.color = color }
        function onUpdateStatusChanged(text, color) { updateStatus.text = text; updateStatus.color = color }
        function onCardStatus(cardId, phase, detail, color, progress, showBar, done) {
            var target = (cardId === "lobby") ? lobbyCard
                       : (cardId === "share" ? shareCard : joinCard)
            target.cardPhase = phase
            target.cardDetail = detail
            target.statusColor = color
            target.showBar = showBar
            target.done = done
            target.progressValue = progress
        }
        function onSavesChanged() {
            saveCombo.currentIndex = -1
            if (bridge.saves.length > 0) saveCombo.currentIndex = 0
        }
    }
}
