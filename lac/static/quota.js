$(function() {
    $("table.quota-size").each(function() {
        var $this = $(this);
        var old_unit =$this.find("select").val();
        var new_unit;
        var new_value;
        $this.find("select").click(function() {
            old_unit = this.value;
        }).change(function() {
            new_unit = this.value;
            new_value = ($this.find("input").val() * (old_unit / new_unit));
            $this.find("input").val(new_value);
        });
    });
});
