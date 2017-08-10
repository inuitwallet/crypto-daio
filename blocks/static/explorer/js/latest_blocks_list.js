/**
 * Created by sammoth on 08/05/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/latest_blocks_list/');

    var latest_blocks_table_rows = $("#latest-blocks-table>tbody tr");
    var first_row = $("#latest-blocks-table>tbody tr:first");

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.listen(function (data, channel) {
            var message_type = data["message_type"];

            if (message_type === "new_block") {
                var block_html = data["block_html"];
                first_row.before(block_html);
            }

            if (message_type === "update_block") {
                var index = data["index"];
                var block_html = data["block_html"];
                var block_is_valid = data["block_is_valid"];
                var row = latest_blocks_table_rows.eq(index);
                row.fadeOut('fast', function () {
                    if (block_is_valid) {
                        row.removeClass("warning")
                    } else {
                        row.addClass("warning")
                    }
                    row.html(block_html).fadeIn('fast')
                });

            }

        });
    });
});
