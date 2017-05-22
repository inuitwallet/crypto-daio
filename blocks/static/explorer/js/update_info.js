/**
 * Created by sammoth on 22/05/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/latest_blocks_list/');

    webSocketBridge.listen(function (data, channel) {
        var message_type = data["message_type"];

        if (message_type === "update_info") {
            var element = $("#" + data["id"]);
            var element_data = $("#" + data["id"] + " span.data");
            var value = data["value"];

            element_data.text(value);
            if (value > 0) {
                element.fadeIn();
            } else {
                element.fadeOut();
            }
        }
    });
});
