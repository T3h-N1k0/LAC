$(function() {
    $("div[data-toggle=fieldset]").each(function() {
        var $this = $(this);
        //Add new entry
        $this.find("button[data-toggle=fieldset-add-row]").click(function() {
            var target = $($(this).data("target"))


            var oldrow = target.find("li:last");
            oldrow.find("li").css('color', 'red');
            var row = oldrow.clone(true, true);
            var elem_id = row.find(":input")[0].id;
            var elem_num = parseInt(elem_id.replace(/.*-(\d{1,4})/m, '$1')) + 1;
            //alert(elem_num)
            row.attr('id', elem_num);
            row.find(":input").each(function() {
                var id = $(this).attr('id').replace('-' + (elem_num - 1), '-' + (elem_num));
                $(this).attr('name', id).attr('id', id).val('').removeAttr("checked");
            });
            oldrow.after(row);
        }); //End add new entry

        //Remove row
        $this.find("button[data-toggle=fieldset-remove-row]").click(function() {
            if($this.find("li").length > 1) {
                $(this).css('color', 'red');
                $(this).closest("li").css('color', 'red');

                var thisRow = $(this).closest("li[data-toggle=fieldset-entry]");
                thisRow.remove();
            }
        }); //End remove row
    });
});
