/**
 * Created by sammoth on 09/06/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/get_block_transactions/');

    var block_hash = $("#block-hash").text();

    var transactions_div = $("#transactions");

    var extra_detail = $('.show-extra-detail');

    transactions_div.on('click', extra_detail, function (e) {
        var tx_id = $(e.target).attr("data");
        var detail = $(e.target).text();
        if (detail === "More Detail") {
            $(".min-detail-" + tx_id).hide('slow');
            $(".full-detail-" + tx_id).show('slow');
            $(e.target).text("Less Detail")
        }
        if (detail === "Less Detail") {
            $(".full-detail-" + tx_id).hide('slow');
            $(".min-detail-" + tx_id).show('slow');
            $(e.target).text("More Detail")
        }

    });

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.stream(block_hash).send({'host': window.location.hostname});
        webSocketBridge.listen(function(data) {
            if (data["message_type"] === "block_transaction"){
                transactions_div.append(data["html"]);
            }
        });
    });
});
