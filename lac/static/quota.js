$(function() {
    $("table[class=quota-size]").each(function() {
        var $this = $(this);
        var old_unit;

        $this.find("select").on('focus', function() {
            old_unit = this.value;
        }).change(function() {
            new_unit = this.value;
            new_value = ($this.find("input").val() * old_unit) / new_unit;
            $this.find("input").val(new_value)
        });
    });
});
