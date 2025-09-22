from django.urls import include, path

from . import views

app_name = "eval"
urlpatterns = [
    path("submit", views.SubmitView.as_view(), name="submit"),
    path(
        "reconstruction",
        views.ReconstructionEntriesView.as_view(),
        name="reconstruction",
    ),
    path("detail/<int:pk>", views.DetailView.as_view(), name="detail"),
    path("edit/<int:pk>", views.EditView.as_view(), name="edit"),
]
