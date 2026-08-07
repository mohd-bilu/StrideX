from django.shortcuts import render

def checkout(request):
    return render(request, "Order/checkout.html")


def place_order(request):
    pass


def order_success(request, order_id):
    return render(request, "Order/order_success.html", {
        "order_id": order_id
    })


def order_list(request):
    return render(request, "Order/order_list.html")


def order_detail(request, order_id):
    return render(request, "Order/order_detail.html", {
        "order_id": order_id
    })


def cancel_order_item(request, item_id):
    pass


def return_order_item(request, item_id):
    pass