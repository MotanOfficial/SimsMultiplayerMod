import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components"

ApplicationWindow {
    id: root
    width: 920
    height: 800
    minimumWidth: 800
    minimumHeight: 660
    visible: true
    title: "Sims 4 Multiplayer - Lobby"
    color: Theme.cBg
    font.family: Theme.fFont

    onClosing: {
        bridge.shutdown()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        // ---------------------------------------------------------- header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                width: 4
                Layout.preferredHeight: 40
                radius: 2
                color: Theme.cAccent
            }
            ColumnLayout {
                spacing: 1
                Text {
                    text: "Sims 4 Multiplayer"
                    color: Theme.cFg
                    font.pixelSize: 20
                    font.bold: true
                }
                Text {
                    text: "LAN co-op lobby - host or join a session"
                    color: Theme.cMuted
                    font.pixelSize: 11
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                id: playerBadge
                text: bridge.playerCount === 1 ? "1 player connected" : bridge.playerCount + " players connected"
                visible: bridge.playerCount > 0
                color: Theme.cGreen
                font.pixelSize: 11
                font.bold: true
                horizontalAlignment: Text.AlignRight
            }
        }

        // -------------------------------------------------------- setup panel
        Rectangle {
            Layout.fillWidth: true
            color: Theme.cPane
            radius: 8
            border.color: Theme.cBorder

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                SectionHeader { label: "Setup" }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 3
                    rows: 3
                    columnSpacing: 8
                    rowSpacing: 6

                    Text {
                        text: "Game files"
                        color: Theme.cMuted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        Layout.preferredWidth: 96
                    }
                    AppTextField {
                        id: fieldGame
                        Layout.fillWidth: true
                        text: bridge.gamePath
                        onTextChanged: bridge.gamePath = text
                    }
                    RowLayout {
                        spacing: 0
                        AppButton {
                            text: "Auto"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.autoFill("game")
                        }
                        AppButton {
                            text: "Browse"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.browse("game")
                        }
                    }

                    Text {
                        text: "Mods folder"
                        color: Theme.cMuted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        Layout.preferredWidth: 96
                    }
                    AppTextField {
                        id: fieldMods
                        Layout.fillWidth: true
                        text: bridge.modsPath
                        onTextChanged: bridge.modsPath = text
                    }
                    RowLayout {
                        spacing: 0
                        AppButton {
                            text: "Auto"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.autoFill("mods")
                        }
                        AppButton {
                            text: "Browse"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.browse("mods")
                        }
                    }

                    Text {
                        text: "Saves folder"
                        color: Theme.cMuted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        Layout.preferredWidth: 96
                    }
                    AppTextField {
                        id: fieldSaves
                        Layout.fillWidth: true
                        text: bridge.savesPath
                        onTextChanged: bridge.savesPath = text
                    }
                    RowLayout {
                        spacing: 0
                        AppButton {
                            text: "Auto"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.autoFill("saves")
                        }
                        AppButton {
                            text: "Browse"
                            fgColor: Theme.cAccent
                            font.bold: false
                            font.pixelSize: 11
                            padding: 6
                            leftPadding: 10
                            rightPadding: 10
                            onClicked: bridge.browse("saves")
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    AppButton {
                        text: "Install mod"
                        bgColor: Theme.cAccent
                        bgHover: Theme.cAccentHover
                        fgColor: "#ffffff"
                        onClicked: bridge.installMod()
                    }
                    AppButton {
                        text: "Check updates"
                        fgColor: Theme.cAccent
                        onClicked: bridge.checkUpdates()
                    }
                    Text {
                        text: "Auto-update"
                        color: Theme.cFg
                        font.pixelSize: 12
                    }
                    Switch {
                        id: autoSwitch
                        checked: bridge.autoUpdate
                        onToggled: bridge.autoUpdate = checked
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        id: setupStatus
                        text: ""
                        font.pixelSize: 12
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }

                Text {
                    id: updateStatus
                    Layout.fillWidth: true
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
        }

        // -------------------------------------------------------------- tabs
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            Layout.topMargin: 2
            background: Rectangle { color: "transparent" }

            TabButton {
                id: hostTabBtn
                text: "  Host a game  "
                font.pixelSize: 12
                font.bold: true
                background: Rectangle {
                    radius: 6
                    color: hostTabBtn.checked ? Theme.cAccent : "transparent"
                }
                contentItem: Text {
                    text: hostTabBtn.text
                    color: hostTabBtn.checked ? "#ffffff" : Theme.cMuted
                    font: hostTabBtn.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
            TabButton {
                id: joinTabBtn
                text: "  Join a game  "
                font.pixelSize: 12
                font.bold: true
                background: Rectangle {
                    radius: 6
                    color: joinTabBtn.checked ? Theme.cAccent : "transparent"
                }
                contentItem: Text {
                    text: joinTabBtn.text
                    color: joinTabBtn.checked ? "#ffffff" : Theme.cMuted
                    font: joinTabBtn.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // ---------------------------------------------------- host page
            Rectangle {
                color: Theme.cPane
                radius: 8
                border.color: Theme.cBorder

                ScrollView {
                    id: hostScroll
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    ColumnLayout {
                        width: hostScroll.availableWidth
                        spacing: 10

                        SectionHeader { label: "Lobby" }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: 8
                            rowSpacing: 6

                            Text {
                                text: "Port"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                Layout.preferredWidth: 64
                            }
                            AppTextField {
                                id: hostPortField
                                Layout.preferredWidth: 90
                                text: bridge.hostPort
                                onTextChanged: bridge.hostPort = text
                            }
                            Text {
                                text: "Your LAN IP"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                Layout.leftMargin: 12
                                Layout.preferredWidth: 84
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                AppComboBox {
                                    id: lanIpCombo
                                    Layout.fillWidth: true
                                    model: bridge.lanIps
                                    Component.onCompleted: currentIndex = bridge.lanIpIndex
                                    onCurrentIndexChanged: bridge.lanIpSelected(currentIndex)
                                }
                                AppButton {
                                    text: "Copy"
                                    fgColor: Theme.cAccent
                                    font.bold: false
                                    font.pixelSize: 11
                                    padding: 6
                                    leftPadding: 10
                                    rightPadding: 10
                                    onClicked: bridge.copyIp()
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: "Your name"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.preferredWidth: 64
                            }
                            AppTextField {
                                Layout.fillWidth: true
                                text: bridge.hostName
                                onTextChanged: bridge.hostName = text
                            }
                        }

                        StatusCard {
                            id: lobbyCard
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: 8
                            AppButton {
                                text: "Start lobby"
                                bgColor: Theme.cAccent
                                bgHover: Theme.cAccentHover
                                fgColor: "#ffffff"
                                enabled: !bridge.lobbyRunning
                                onClicked: bridge.startLobby()
                            }
                            AppButton {
                                text: "Stop lobby"
                                fgColor: Theme.cRed
                                enabled: bridge.lobbyRunning
                                onClicked: bridge.stopLobby()
                            }
                        }

                        SectionHeader { label: "Save to share" }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            AppComboBox {
                                id: saveCombo
                                Layout.fillWidth: true
                                model: bridge.saves
                                enabled: bridge.saves.length > 0
                                onCurrentIndexChanged: bridge.selectSave(currentIndex)
                            }
                            AppButton {
                                text: "Refresh"
                                fgColor: Theme.cAccent
                                font.bold: false
                                font.pixelSize: 11
                                padding: 6
                                leftPadding: 10
                                rightPadding: 10
                                onClicked: bridge.refreshSaves()
                            }
                        }

                        StatusCard {
                            id: shareCard
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: 8
                            AppButton {
                                text: "Share save with players"
                                fgColor: Theme.cAccent
                                enabled: bridge.canShare
                                onClicked: bridge.shareSave()
                            }
                            AppButton {
                                text: "Start game"
                                bgColor: Theme.cGreen
                                bgHover: Theme.cGreen
                                fgColor: "#0d1f17"
                                enabled: bridge.canHostStart
                                onClicked: bridge.startGameHost()
                            }
                        }
                    }
                }
            }

            // ---------------------------------------------------- join page
            Rectangle {
                color: Theme.cPane
                radius: 8
                border.color: Theme.cBorder

                ScrollView {
                    id: joinScroll
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    ColumnLayout {
                        width: joinScroll.availableWidth
                        spacing: 10

                        SectionHeader { label: "Lobby address" }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 6
                            columnSpacing: 8
                            rowSpacing: 6

                            Text {
                                text: "Host IP"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                Layout.preferredWidth: 64
                            }
                            AppTextField {
                                Layout.fillWidth: true
                                Layout.columnSpan: 5
                                text: bridge.joinIp
                                onTextChanged: bridge.joinIp = text
                            }

                            Text {
                                text: "Port"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                Layout.preferredWidth: 64
                            }
                            AppTextField {
                                Layout.preferredWidth: 90
                                text: bridge.joinPort
                                onTextChanged: bridge.joinPort = text
                            }
                            Text {
                                text: "Your name"
                                color: Theme.cMuted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                Layout.leftMargin: 12
                                Layout.preferredWidth: 84
                            }
                            AppTextField {
                                Layout.fillWidth: true
                                text: bridge.joinName
                                onTextChanged: bridge.joinName = text
                            }
                        }

                        StatusCard {
                            id: joinCard
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: 8
                            AppButton {
                                text: bridge.joining ? "Joining..." : "Join lobby"
                                bgColor: Theme.cAccent
                                bgHover: Theme.cAccentHover
                                fgColor: "#ffffff"
                                enabled: !bridge.joining
                                onClicked: bridge.joinLobby()
                            }
                            AppButton {
                                text: "Start game"
                                bgColor: Theme.cGreen
                                bgHover: Theme.cGreen
                                fgColor: "#0d1f17"
                                enabled: bridge.canJoinStart
                                onClicked: bridge.startGameJoin()
                            }
                        }
                    }
                }
            }
        }

        // ------------------------------------------------------- activity log
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            color: Theme.cPane
            radius: 8
            border.color: Theme.cBorder

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "ACTIVITY"
                        color: Theme.cMuted
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 1.2
                    }
                    Item { Layout.fillWidth: true }
                    AppButton {
                        text: "Clear"
                        fgColor: Theme.cAccent
                        font.bold: false
                        font.pixelSize: 11
                        padding: 6
                        leftPadding: 10
                        rightPadding: 10
                        onClicked: logModel.clear()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0f1116"
                    radius: 6

                    ListView {
                        id: logList
                        anchors.fill: parent
                        anchors.margins: 6
                        clip: true
                        model: ListModel { id: logModel }
                        spacing: 1
                        ScrollBar.vertical: ScrollBar {}
                        onCountChanged: positionViewAtEnd()
                        delegate: Text {
                            width: logList.width - 14
                            text: model.line
                            color: model.kind === "error" ? Theme.cRed
                                 : (model.kind === "muted" ? Theme.cMuted : Theme.cFg)
                            font.family: Theme.fMono
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }
        }
    }

    // ----------------------------------------------------------- bridge glue
    Connections {
        target: bridge
        function onLogAppended(line, kind) { logModel.append({ "line": line, "kind": kind }) }
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