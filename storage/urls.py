from django.urls import path
from . import views

urlpatterns = [
    path('index/', views.index, name='index'),
    path('', views.dashboard, name='dashboard'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('security/', views.security, name='security'),
    path('support/', views.support, name='support'),
    path('upload/', views.upload_file, name='upload_file'),
    path('create-folder/', views.create_folder, name='create_folder'),
    path('folder/<int:folder_id>/contents/', views.folder_contents, name='folder_contents'),
    path('delete/<str:item_type>/<int:item_id>/', views.delete_item, name='delete_item'),
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('search/', views.search, name='search'),
    path('starred/', views.starred_files, name='starred_files'),
    path('recent/', views.recent_files, name='recent_files'),
    path('rename/<str:item_type>/<int:item_id>/', views.rename_item, name='rename_item'),
    path('toggle-star/<int:file_id>/', views.toggle_star, name='toggle_star'),
    path('subscription/', views.subscription_plans, name='subscription_plans'),
    path('subscription/upgrade/<str:plan_name>/', views.upgrade_subscription, name='upgrade_subscription'),
    path('subscription/downgrade/', views.downgrade_subscription, name='downgrade_subscription'),
    
    path('subscription/checkout/<str:plan_name>/', views.checkout, name='checkout'),
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    path('payment-methods/set-default/<int:payment_method_id>/', views.set_default_payment_method, name='set_default_payment_method'),


]