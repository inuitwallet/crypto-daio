/**
 * Created by sammoth on 22/05/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/update-info/');

    webSocketBridge.listen(function (data, channel) {
        if (data["message_type"] === "update_info") {
            var element = $("#" + data["id"]);
            var element_data = $("#" + data["id"] + " div.data");
            var value = data["value"];

            element_data.text(value);
            if (value == 0) {
                element.hide();
            }
        }
    });
});
