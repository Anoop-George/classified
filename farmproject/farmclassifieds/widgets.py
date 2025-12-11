from django.forms.widgets import ClearableFileInput


class MultiFileInput(ClearableFileInput):
    """
    File input that supports selecting multiple files.
    Works with Django 4.2+.
    """
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        # request.FILES is a MultiValueDict, so we must use getlist()
        if hasattr(files, "getlist"):
            return files.getlist(name)
        return []
