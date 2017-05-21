/**
 * Created by sammoth on 08/05/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/latest_blocks_list/');

    var latest_blocks_table = $("#latest-blocks-table>tbody");
    var latest_blocks_table_rows = $("#latest-blocks-table>tbody tr");
    var first_row = $("#latest-blocks-table>tbody tr:first");

    webSocketBridge.listen(function (data, channel) {
        var message_type = data["message_type"];

        if (message_type === "new_block") {
            var block_html = data["block_html"];
            first_row.before(block_html);
        }

    });
});
