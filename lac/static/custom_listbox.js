function selectFromList(availableList, selectedList)
{
    // loop through first listbox and append to second listbox
    $(availableList + ' :selected').each(function(i, selected){
        // append to second list box
        $(selectedList).append('<option value="'+selected.value+'">'+ selected.text+'</option>');
        // remove from first list box
        $(availableList + " option[value='"+ selected.value +"']").remove();
     });
    //selectAll(selectedList, true)
}
function removeFromList(availableList, selectedList)
{
    // loop through second listbox and append to first listbox
    $(selectedList + ' :selected').each(function(i, selected){
        // append to first list box
        $(availableList).append('<option value="'+selected.value+'">'+ selected.text+'</option>');
         // remove from second list box
        $(selectedList + " option[value='"+ selected.value +"']").remove();
    });
}

// Function for Filtering
function searchFromList(inputVal, searchArea)
{
    var allCells = $(searchArea).find('option');

    if(allCells.length > 0)
    {
        var found = false;
        allCells.each(function(index, option) {
            var regExp = new RegExp(inputVal, 'i');
            if(regExp.test($(option).text()))
                $(option).show();
            else
                $(option).hide();
        });
    }
}
