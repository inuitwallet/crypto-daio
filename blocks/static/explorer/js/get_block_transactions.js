/**
 * Created by sammoth on 09/06/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/get_block_transactions/');

    var block_hash = $("#block-hash").text();

    var transactions_div = $("#transactions");
    var grants_div = $("#grants");
    var motions_div = $("#motions");

    var extra_detail = $('.show-extra-detail');

    transactions_div.on('click', extra_detail, function (e) {
        var tx_id = $(e.target).attr("data");
        var detail = $(e.target).text();
        if (detail === "Show Advanced Details") {
            $(".min-detail-" + tx_id).fadeOut('fast', function() {
                $(".full-detail-" + tx_id).fadeIn('fast');
                $(e.target).text("Hide Advanced Details");
            });
        }
        if (detail === "Hide Advanced Details") {
            $(".full-detail-" + tx_id).fadeOut('fast', function() {
                $(".min-detail-" + tx_id).fadeIn('fast');
                $(e.target).text("Show Advanced Details");
            });
        }

    });

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.stream(block_hash).send({'host': window.location.hostname});
        webSocketBridge.listen(function(data) {
            if (data["message_type"] === "clear_block_transactions"){
                transactions_div.empty();
                grants_div.empty();
                motions_div.empty();
            }
            if (data["message_type"] === "block_transaction"){
                transactions_div.append(data["html"]);
            }
            if (data["message_type"] === "has_grants"){
                alert("yo");
                $(".grants").show()
            }
            if (data["message_type"] === "block_grant"){
                grants_div.append(data["html"]);
            }
        });
    });
});
