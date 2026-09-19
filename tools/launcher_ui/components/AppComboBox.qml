import QtQuick
import QtQuick.Controls
import ".."

ComboBox {
    id: combo
    font.family: Theme.fFont
    font.pixelSize: 12
    padding: 8
    contentItem: Text {
        text: combo.displayText
        color: Theme.cFg
        font: combo.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 4
        color: Theme.cField
        border.color: combo.activeFocus ? Theme.cAccent : Theme.cBorder
        border.width: 1
    }
    indicator: Text {
        x: combo.width - 24
        y: combo.height / 2 - contentHeight / 2
        text: "\u25be"
        color: Theme.cMuted
        font.pixelSize: 13
    }
    popup: Popup {
        y: combo.height + 3
        width: combo.width
        implicitHeight: contentItem.implicitHeight + 4
        padding: 2
        background: Rectangle {
            radius: 4
            color: Theme.cPane
            border.color: Theme.cBorder
        }
        contentItem: ListView {
            implicitHeight: contentHeight
            model: combo.popup.visible ? combo.delegateModel : null
            clip: true
            currentIndex: combo.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }
    delegate: ItemDelegate {
        id: row
        width: combo.width - 4
        height: 32
        highlighted: combo.highlightedIndex === index
        contentItem: Text {
            text: {
                var m = (typeof model === "undefined") ? null : model
                if (m !== null && m.hasOwnProperty("modelData")) return m.modelData
                if (m !== null && m.hasOwnProperty("text")) return m.text
                return String(m)
            }
            color: row.highlighted ? "#ffffff" : Theme.cFg
            font: combo.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 3
            color: row.highlighted ? Theme.cAccent : "transparent"
        }
    }
}