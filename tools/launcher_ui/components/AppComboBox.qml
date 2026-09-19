import QtQuick
import QtQuick.Controls
import ".."

ComboBox {
    id: combo
    implicitHeight: 40
    font.family: Theme.fFont
    font.pixelSize: 12
    padding: 12
    contentItem: Text {
        text: combo.displayText
        color: Theme.cFgDark
        font: combo.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 6
        color: Theme.cField
        border.width: 1
        border.color: !combo.enabled ? "#e0e0e0"
                     : (combo.activeFocus || combo.popup.visible ? Theme.cAccent : Theme.cFieldBorder)
    }
    indicator: Text {
        x: combo.width - 26
        y: combo.height / 2 - contentHeight / 2
        text: "\u25be"
        color: "#666666"
        font.pixelSize: 12
    }
    popup: Popup {
        y: combo.height + 4
        width: combo.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 220)
        padding: 4
        background: Rectangle {
            radius: 6
            color: "#ffffff"
            border.color: Theme.cFieldBorder
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
        implicitHeight: 34
        width: combo.width - 8
        highlighted: combo.highlightedIndex === index
        contentItem: Text {
            text: {
                var m = (typeof model === "undefined") ? null : model
                if (m !== null && m.hasOwnProperty("modelData")) return m.modelData
                if (m !== null && m.hasOwnProperty("text")) return m.text
                return String(m)
            }
            color: row.highlighted ? "#ffffff" : Theme.cFgDark
            font: combo.font
            leftPadding: 10
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 4
            color: row.highlighted ? Theme.cAccent : "transparent"
        }
    }
}