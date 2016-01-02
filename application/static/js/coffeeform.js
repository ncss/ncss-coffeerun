$(document).ready(function() {
    //var sizes = {"S": 3.0, "M": 3.5, "L": 4.0};
    var sizes = {};
    var origrun = $("#runid option:selected").val();
    var origsize = $("#size option:selected").val();
    $("#size").change(function() {
        var size = $("#size option:selected").text();
        $("#price").val(sizes[size]).number(true, 2);
    });
    $("#runid").change(function() {
        $.getJSON($SCRIPT_ROOT + "/_prices_for_run/", {
            runid: $(this).val()
        }, function(data) {
            sizes = {};
            $("#size").find("option").remove();
            $.each(data, function(key, val) {
                sizes[key] = val;
                var optStr = '<option value="' + key + '">' + key + '</option>';
                $("#size").append(optStr);
            });
            $("#size").val(origsize);
            $("#size").change();
        });
    });
    $("#recurring").change(function() {
        if ($(this).is(":checked")) {
            $(".recurringFields").show();
        } else {
            $(".recurringFields").hide();
        }
    });

    $("#runid").val(origrun);
    $("#runid").change();
    $("#size").change();
    $("#recurring").change();

});
