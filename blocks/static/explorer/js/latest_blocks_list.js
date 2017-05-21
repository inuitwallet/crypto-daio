/**
 * Created by sammoth on 08/05/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/latest_blocks_list/');

    var latest_blocks_table = $("#latest-blocks-table>tbody");
    var latest_blocks_table_rows = $("#latest-blocks-table>tbody tr");

    webSocketBridge.listen(function (data, channel) {
        var block_height = data["block_height"];
        $(latest_blocks_table_rows).each(function () {
            var height = $(this).find('td.height').text();
            if (block_height > height) {
                alert(block_height);
                $(this).insertBefore(data['block_html']);
            }
        })
    });
});
