$(function() {
    $("table.quota-size").each(function() {
        var $this = $(this);
        $this.find("select").click(function() {
            old_unit = this.value;
        }).change(function() {
            var new_unit = this.value;
            var new_value = ($this.find("input").val() * (old_unit / new_unit));
            $this.find("input").val(new_value);
        });
    });
});
