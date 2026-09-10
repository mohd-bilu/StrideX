<div align="center">

# 👟 STRIDEX — Premium Footwear E-Commerce Platform

**A full-featured Django e-commerce application designed for a modern footwear shopping experience.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Razorpay](https://img.shields.io/badge/Razorpay-02042B?style=for-the-badge&logo=razorpay&logoColor=white)](https://razorpay.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)

</div>

---

## 📖 Project Overview

**STRIDEX** is a full-stack footwear e-commerce platform built with Django.

The application provides customers with a complete online shopping experience, including account registration, OTP verification, product browsing, product variants, wishlist management, shopping cart, Buy Now functionality, checkout, coupons, offers, multiple payment methods, wallet management, order tracking, cancellation, refunds, invoices, and referral rewards.

The platform also includes a dedicated custom administration panel that allows administrators to manage customers, categories, products, product variants, coupons, offers, orders, and sales reports.

StrideX focuses on providing a clean shopping experience while maintaining secure authentication, server-side validation, accurate pricing calculations, stock management, secure payment processing, and reliable order handling.

---

## ✨ Key Highlights

- 🔐 **OTP-based email verification** during user registration
- 🔑 **Secure login and logout** functionality
- 🔄 **OTP-based forgot password** and password reset
- 📧 **Change email verification** using OTP
- 🔒 **Strong password validation** with centralized validation rules
- 👤 **User profile management** with profile editing
- 🏠 **Multiple address management** with default address support
- 🛍️ **Complete footwear shopping flow** from product browsing to order placement
- 🎨 **Product variant management** for size, color, price, stock, and images
- 🛒 **Shopping Cart** with quantity and stock validation
- ❤️ **Wishlist** management
- ⚡ **Buy Now** direct checkout functionality
- 🎟️ **Coupon system** supporting percentage and fixed discounts
- 🏷️ **Product and Category Offers** with automatic discount calculation
- 💳 **Razorpay** online payment integration
- 💰 **Digital Wallet** with balance and transaction history
- 🎁 **Referral system** with unique referral codes and rewards
- 📦 **Complete order lifecycle** management
- ❌ **Order cancellation** with cancellation reason
- 💸 **Wallet refund** support for eligible cancellations
- 🧾 **PDF invoice** generation and download
- 📊 **Sales reports** for administrators
- 📈 **Revenue and order analysis**
- 👨‍💼 **Custom admin management panel**
- 🖼️ **Product variant image management**
- 🔒 **Authentication protection** for customer actions
- ⚠️ **Custom 400, 403, 404, and 500 error pages**
- 📱 **Responsive user interface**
- ✨ **SweetAlert notifications** for user feedback

---

## 👤 User Features

### Authentication & Account

| Feature | Details |
|---|---|
| **Registration** | User registration using full name, email, password, and confirmation password |
| **OTP Verification** | Email-based OTP verification for new user accounts |
| **OTP Resend** | Resend OTP functionality for account verification |
| **Login** | Secure email and password authentication |
| **Logout** | Secure logout with confirmation modal and POST request |
| **Forgot Password** | OTP-based password recovery |
| **Reset Password** | Secure password reset with strong password validation |
| **Change Password** | Change existing password with validation |
| **Change Email** | Change account email after OTP verification |
| **Email Verification** | Verify the newly entered email address through OTP |
| **Referral Code** | Automatically generated unique referral code |
| **Referral Tracking** | Referrer relationship stored during signup |
| **Blocked Accounts** | Blocked users are prevented from accessing the account |

### Profile & Account Management

- View personal profile information
- Edit profile information
- Update full name
- Update phone number
- Change account email
- Change account password
- View personal referral code
- Copy referral code for sharing
- Display referral information
- Secure authenticated profile access
- Logout confirmation modal
- User-friendly validation messages
- SweetAlert-based success and error notifications

### Address Management

- Add multiple delivery addresses
- Edit saved addresses
- Delete saved addresses
- Set a default address
- Home, Office, and Other address types
- Full name validation
- Phone number validation
- Street address validation
- City validation
- State validation
- Pincode validation
- Country validation
- Address type validation
- Secure address ownership checks
- Add address directly from checkout
- Edit address directly from checkout
- Return to checkout after address changes
- Secure checkout navigation using validated `next` parameters

---

## 🛍️ Product Browsing

### Product Listing

- Browse active footwear products
- Display available products by category
- Display product images
- Display product prices
- Display product availability
- Display active product variants
- Display applicable offers
- Similar product suggestions
- Responsive product layout
- Guest users can browse products without authentication

### Product Detail

- View detailed product information
- View product description
- View product variants
- Select available size
- Select available color
- Display variant-specific images
- Display variant-specific price
- Display available stock
- Add selected variant to cart
- Add selected variant to wishlist
- Buy selected variant immediately
- Display applicable product offers
- Display discounted offer price
- Display similar products
- Prevent unavailable variants from being purchased
- Login protection for cart and wishlist actions

### Product Offers

- Product-specific offers
- Category-based offers
- Percentage-based discounts
- Fixed amount discounts
- Offer start dates
- Offer expiry dates
- Active/inactive offer status
- Automatic offer validation
- Best applicable offer calculation
- Offer-aware product pricing
- Offer-aware checkout pricing
- Offer-aware order totals

---

## 🛒 Cart & Wishlist

### Shopping Cart

- Add product variants to cart
- Increase item quantity
- Decrease item quantity
- Remove cart items
- Display cart item quantity
- Display product information
- Display variant information
- Display item price
- Calculate item subtotal
- Calculate cart subtotal
- Validate available stock
- Prevent quantity from exceeding stock
- Handle unavailable variants
- AJAX-based cart operations
- Dynamic cart count
- Authentication protection for cart actions

### Wishlist

- Add products to wishlist
- Remove products from wishlist
- View wishlist items
- Variant-based wishlist handling
- AJAX wishlist operations
- Authentication protection
- Login notification for guest users
- Move products from wishlist to cart
- Maintain wishlist state across the account

### Buy Now

- Direct purchase from product detail
- Select variant before purchase
- Select quantity before purchase
- Direct checkout without changing the normal cart
- Dedicated Buy Now session handling
- Prevent cart products from being mixed with Buy Now checkout
- Preserve normal cart after Buy Now purchase
- Process Buy Now order independently

---

## 💳 Checkout & Orders

### Checkout

- Display selected products
- Display selected variants
- Display quantities
- Select saved delivery address
- Add new delivery address
- Edit existing delivery address
- Return to checkout after address changes
- Apply available coupon
- Remove applied coupon
- Calculate product offer discount
- Calculate coupon discount
- Combine offer and coupon discounts
- Calculate shipping charges
- Calculate final payable amount
- Validate stock before placing order
- Validate coupon before order placement
- Validate offer validity before order placement
- Maintain accurate checkout totals

### Payment Methods

- **Cash on Delivery**
- **Razorpay Online Payment**
- **Wallet Payment**

### Razorpay Payment

- Create Razorpay payment order
- Calculate payment amount on the server
- Process online payment
- Verify Razorpay payment response
- Handle successful payments
- Handle cancelled payments
- Handle failed payments
- Maintain payment status
- Prevent incorrect payment totals
- Secure payment processing

### Wallet Payment

- Check wallet balance
- Validate sufficient balance
- Deduct wallet amount during checkout
- Create wallet debit transaction
- Associate wallet transaction with order
- Prevent insufficient balance payments
- Maintain wallet transaction history

### Order Placement

- Validate selected address
- Validate cart items
- Validate product stock
- Calculate product offer discounts
- Calculate coupon discounts
- Calculate shipping charges
- Calculate final order amount
- Create order record
- Create order items
- Store delivery address snapshot
- Store subtotal
- Store total discount
- Store offer discount
- Store coupon discount
- Store shipping amount
- Store final order total
- Store payment method
- Store payment status
- Reduce product stock
- Clear successfully purchased cart items

### Order Management

- View order history
- View individual order details
- Display order date
- Display order status
- Display payment status
- Display order total
- Display ordered products
- Display product variants
- Display quantities
- Display delivery address
- Display cancellation information
- Download eligible invoice
- Track order status through the user account

### Order Cancellation

- Cancel eligible orders
- Require cancellation reason
- Validate cancellation request
- Update order status
- Restore product stock
- Process eligible wallet refunds
- Maintain cancellation information
- Prevent invalid cancellation attempts
- Display cancellation status to the customer

---

## 🎟️ Coupon System

### Coupon Features

- Create discount coupons
- Percentage discount coupons
- Fixed amount coupons
- Minimum purchase requirement
- Maximum discount limit
- Coupon start date
- Coupon expiry date
- Coupon usage limit
- Active/inactive coupon status
- Per-user coupon usage tracking
- Prevent repeated coupon usage
- Prevent expired coupon usage
- Prevent future coupon usage
- Prevent exhausted coupon usage
- Validate minimum purchase requirement
- Validate positive discount amount

### Coupon Checkout Integration

- Apply coupon directly from checkout
- Validate coupon on the server
- Calculate coupon discount
- Apply coupon after offer discount
- Combine coupon and offer discounts
- Remove applied coupon
- Recalculate checkout total
- Maintain selected coupon during checkout
- Prevent client-side price manipulation
- Prevent invalid coupon usage

### Available Coupons

- Display available coupons
- Display coupon code
- Display discount information
- Display minimum purchase requirement
- Display expiry date
- Display coupon availability
- Use coupon from available coupon page
- Pass selected coupon to checkout
- Automatically remove used coupons from available user coupons

---

## 🏷️ Offer System

### Product Offers

- Create product-specific offers
- Select product for an offer
- Configure percentage discount
- Configure fixed discount
- Configure offer start date
- Configure offer expiry date
- Activate or deactivate offers
- Automatically detect active offers
- Apply best applicable offer

### Category Offers

- Create category-based offers
- Select category for an offer
- Configure percentage discount
- Configure fixed discount
- Configure offer validity
- Activate or deactivate offers
- Validate category offer configuration
- Automatically apply applicable category offers

### Offer Calculation

- Detect currently active offers
- Ignore expired offers
- Ignore future offers
- Identify product-specific offers
- Identify category-specific offers
- Compare applicable offers
- Select the best available offer
- Calculate offer discount
- Apply discount to product pricing
- Apply discount during checkout
- Store offer discount in order records
- Include offer discount in order calculations
- Maintain consistent pricing throughout checkout

---

## 💰 Wallet

- Create wallet for eligible users
- Display current wallet balance
- Display wallet transaction history
- Display credit transactions
- Display debit transactions
- Deduct wallet payments
- Credit eligible refunds
- Credit referral rewards
- Maintain transaction descriptions
- Maintain transaction references
- Validate available balance
- Prevent invalid wallet deductions
- Support wallet payment during checkout

### Referral Rewards

- Automatically generate unique referral code
- Display referral code in profile
- Allow users to share referral code
- Accept referral code during signup
- Store referring user
- Track referred users
- Validate referral eligibility
- Check first delivered order eligibility
- Credit reward to referrer's wallet
- Create referral wallet transaction
- Prevent duplicate referral rewards
- Maintain referral reward status

---

## 🛠️ Admin Features

### Dashboard

- Dedicated custom administration dashboard
- Customer overview
- Product overview
- Order overview
- Revenue information
- Sales information
- Recent order information
- Low-stock information
- Quick administrative navigation
- Management shortcuts
- Overview of ecommerce activity

### User Management

- View registered users
- Display customer information
- Sort users
- Block user accounts
- Unblock user accounts
- Prevent blocked users from logging in
- Manage customer account status
- Maintain secure administrative access

### Category Management

- View categories
- Add categories
- Edit categories
- Activate categories
- Deactivate categories
- Soft-delete categories
- Manage category information
- Manage category images
- Validate category data
- Prevent invalid category operations

### Product Management

- View products
- Add products
- Edit products
- Assign products to categories
- Activate products
- Deactivate products
- Soft-delete products
- Manage product information
- Manage product descriptions
- Manage product status
- Validate product information

### Variant Management

- Add product variants
- Edit product variants
- Manage variant size
- Manage variant color
- Manage variant price
- Manage variant stock
- Manage SKU
- Activate or deactivate variants
- Soft-delete variants
- Add variant images
- Delete variant images
- Manage default variant image
- Validate variant information
- Maintain product-variant relationships

### Order Management

- View customer orders
- Filter orders
- View order details
- View ordered products
- View variant information
- View payment information
- View delivery information
- Update order status
- Manage pending orders
- Manage shipped orders
- Manage out-for-delivery orders
- Manage delivered orders
- Manage cancelled orders
- Process eligible cancellation refunds
- Restore stock for cancelled orders

### Coupon Management

- Create coupons
- Edit coupons
- Delete coupons
- Activate coupons
- Deactivate coupons
- Configure coupon code
- Configure discount type
- Configure discount value
- Configure minimum purchase
- Configure maximum discount
- Configure start date
- Configure expiry date
- Configure usage limit
- Track coupon usage
- Prevent invalid coupon configurations
- Display exhausted coupon status

### Offer Management

- Create product offers
- Create category offers
- Edit offers
- Delete offers
- Activate offers
- Deactivate offers
- Configure discount type
- Configure discount value
- Configure start date
- Configure expiry date
- Validate offer configuration
- Prevent invalid offer configurations
- Automatically calculate applicable offers

### Sales Reports

- Daily sales reports
- Weekly sales reports
- Monthly sales reports
- Yearly sales reports
- Custom date range reports
- Total order calculation
- Total revenue calculation
- Net revenue calculation
- Total discount calculation
- Offer discount calculation
- Coupon discount calculation
- Cancelled amount calculation
- Refunded amount calculation
- Products sold calculation
- Average order value calculation
- Revenue trend analysis
- Paginated report data
- Excel report export
- PDF report export

---

## 🏗️ Tech Stack

| Category | Technology |
|---|---|
| **Backend Framework** | Django |
| **Programming Language** | Python |
| **Database** | PostgreSQL |
| **Authentication** | Django Authentication |
| **Payment Gateway** | Razorpay |
| **Frontend** | HTML5, CSS3, JavaScript |
| **UI Notifications** | SweetAlert2 |
| **Image Processing** | Pillow |
| **PDF Generation** | ReportLab |
| **Excel Export** | OpenPyXL |
| **Database Access** | Django ORM |
| **Template Engine** | Django Templates |
| **Version Control** | Git & GitHub |
| **Development Environment** | Python Virtual Environment |
| **Deployment Target** | Production WSGI Server |
| **Time Zone** | Asia/Kolkata (IST) |

---

## 📁 Project Structure

```text
StrideX/

├── Admin_panel/         # Custom administration interface

│   ├── Admin_account/   # Admin authentication and dashboard

│   ├── category/        # Category management

│   ├── product/         # Product, variant and image management

│   ├── coupon_offer/    # Coupon and offer management

│   ├── order/           # Order management

│   └── sales_report/    # Sales reports and exports

├── User_panel/          # Customer-facing application

│   ├── Authentication/  # Signup, login, OTP, profile and addresses

│   ├── Cart/            # Shopping cart and wishlist

│   ├── Checkout/        # Checkout, coupons, offers and payments

│   ├── Order/           # Orders, cancellation and invoices

│   ├── Product/         # Product listing and product details

│   └── Wallet/          # Wallet balance, transactions and refunds

├── StrideX/             # Django project configuration

│   ├── __init__.py      # Python package initialization

│   ├── asgi.py          # ASGI configuration

│   ├── middleware.py    # Custom middleware

│   ├── settings.py      # Django project settings

│   ├── urls.py          # Root URL configuration

│   ├── views.py         # Project-level views

│   └── wsgi.py          # WSGI configuration

├── media/               # Uploaded media files

├── static/              # Static CSS, JavaScript and image files

├── manage.py             # Django management utility

├── requirements.txt      # Python project dependencies

└── README.md             # Project documentation
