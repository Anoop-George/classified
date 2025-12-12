from django import forms

class MultiFileField(forms.FileField):
    def to_python(self, data):
        """Return list instead of a single file."""
        if not data:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def validate(self, data):
        """Override default validate to accept lists."""
        if self.required and not data:
            raise forms.ValidationError("Please upload at least one file.")
        return
