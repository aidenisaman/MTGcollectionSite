$(document).ready(function() {
    $('#cardName').autocomplete({
        source: function(request, response) {
            $.getJSON("/autocomplete", { q: request.term }, function(data) {
                response(data);
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $('#cardName').val(ui.item.value);
            $('#searchButton').click();
        }
    });

    $('#searchButton').click(function() {
        var cardName = $('#cardName').val();
        var cardType = $('#cardType').val();
        var cardColor = $('#cardColor').val();
        if (cardName) {
            $('#loading').show();
            $('#results').empty();
            $.ajax({
                url: '/search',
                method: 'POST',
                data: { 
                    card_name: cardName,
                    card_type: cardType,
                    card_color: cardColor
                },
                success: function(data) {
                    $('#loading').hide();
                    if (data.length === 0) {
                        $('#results').html('<p class="text-red-500">No cards found.</p>');
                    } else {
                        data.forEach(function(card) {
                            var cardHtml = `
                                <div class="bg-gray-800 p-4 rounded-lg relative">
                                    <img src="${card.image_url}" alt="${card.name}" class="w-full h-auto mb-4 rounded">
                                    <p class="font-bold">${card.name}</p>
                                    <p>Set: ${card.set_name}</p>
                                    <p>Type: ${card.type_line}</p>
                                    <p>Colors: ${card.colors.join(', ')}</p>
                                    <p>USD: ${formatPrice(card.usd_price)}</p>A
                                    <p>USD Foil: ${formatPrice(card.usd_foil_price)}</p>
                                    <div class="mt-4">
                                        <button class="add-to-collection bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-2 rounded mr-2" data-card='${JSON.stringify(card)}' data-foil="false">
                                            Add to Collection
                                        </button>
                                        <button class="add-to-collection bg-purple-500 hover:bg-purple-700 text-white font-bold py-1 px-2 rounded" data-card='${JSON.stringify(card)}' data-foil="true">
                                            Add Foil to Collection
                                        </button>
                                    </div>
                                </div>
                            `;
                            $('#results').append(cardHtml);
                        });
                    }
                },
                error: function() {
                    $('#loading').hide();
                    $('#results').html('<p class="text-red-500">An error occurred. Please try again.</p>');
                }
            });
        }
    });

    $(document).on('click', '.add-to-collection', function() {
        var card = $(this).data('card');
        var isFoil = $(this).data('foil') === true;
        card.is_foil = isFoil;
        card.price = isFoil ? card.usd_foil_price : card.usd_price;
        
        if (card.price === 'N/A') {
            card.price = null;
        } else if (card.price !== null) {
            card.price = parseFloat(card.price);
        }
        
        $.ajax({
            url: '/add_to_collection',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(card),
            success: function(response) {
                if (response.success) {
                    showNotification('Card added to your collection!', 'success');
                } else {
                    showNotification('Failed to add card to collection. Please try again.', 'error');
                }
            },
            error: function() {
                showNotification('Failed to add card to collection. Please try again.', 'error');
            }
        });
    });
    $(document).on('click', '.remove-from-collection', function() {
        var cardId = $(this).data('card-id');
        var cardElement = $(this).closest('.card-container');
        
        $.ajax({
            url: '/remove_from_collection',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({id: cardId}),
            success: function() {
                showNotification('Card removed from your collection!', 'success');
                cardElement.fadeOut(300, function() {
                    $(this).remove();
                    updateTotalValue();
                });
            },
            error: function() {
                showNotification('Failed to remove card from collection. Please try again.', 'error');
            }
        });
    });

    function updateTotalValue() {
        var total = 0;
        $('.card-price').each(function() {
            var price = parseFloat($(this).text().replace('$', ''));
            if (!isNaN(price)) {
                total += price;
            }
        });
        $('#total-value').text('$' + total.toFixed(2));
    }

    function formatPrice(price) {
        if (price === 'N/A' || price === null) {
            return 'N/A';
        }
        return '$' + parseFloat(price).toFixed(2);
    }

    function showNotification(message, type) {
        var notificationClass = type === 'success' ? 'bg-green-500' : 'bg-red-500';
        var notification = $(`
            <div class="fixed top-4 right-4 p-4 rounded-lg text-white ${notificationClass} opacity-0 transition-opacity duration-300">
                ${message}
            </div>
        `);
        $('body').append(notification);
        setTimeout(() => {
            notification.addClass('opacity-100');
        }, 100);
        setTimeout(() => {
            notification.removeClass('opacity-100');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
});
