from django import forms
from .models import Lga, Ward, PollingUnit


class NewPollingUnitResultsForm(forms.Form):
    """Capture a new polling unit and a score for every party in the party table."""

    lga = forms.ModelChoiceField(
        queryset=Lga.objects.order_by("lga_name"),
        empty_label="Choose a local government",
        label="Local government area",
    )
    ward = forms.ModelChoiceField(
        queryset=Ward.objects.order_by("ward_name"),
        empty_label="Choose a ward",
        label="Ward",
    )
    polling_unit_id = forms.IntegerField(
        min_value=1, label="Polling unit ID",
        help_text="The number assigned within this ward. It need not be unique across the state.",
    )
    polling_unit_name = forms.CharField(
        max_length=50, label="Polling unit name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Community Primary School"}),
    )
    polling_unit_number = forms.CharField(
        max_length=50, required=False, label="Polling unit code (optional)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. DT2202008"}),
    )
    entered_by_user = forms.CharField(
        max_length=50, label="Entered by",
        widget=forms.TextInput(attrs={"placeholder": "Your name"}),
    )

    def __init__(self, *args, parties, **kwargs):
        super().__init__(*args, **kwargs)
        self.parties = parties

        for party in parties:
            self.fields[f"score_{party.pk}"] = forms.IntegerField(
                min_value=0,
                label=party.partyname,
                initial=0,
                widget=forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            )

        classes = (
            "block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 "
            "text-sm text-slate-900 shadow-sm outline-none transition "
            "placeholder:text-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100 "
            "disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = classes

    @property
    def unit_fields(self):
        return [self[name] for name in (
            "lga", "ward", "polling_unit_id", "polling_unit_name",
            "polling_unit_number", "entered_by_user",
        )]

    @property
    def score_fields(self):
        return [self[f"score_{party.pk}"] for party in self.parties]

    def clean(self):
        data = super().clean()
        lga, ward, polling_unit_id = (
            data.get("lga"), data.get("ward"), data.get("polling_unit_id")
        )
        if lga and ward and ward.lga_id != lga.lga_id:
            self.add_error("ward", "This ward does not belong to the selected LGA.")

        if lga and ward and polling_unit_id is not None and ward.lga_id == lga.lga_id:
            already_exists = PollingUnit.objects.filter(
                lga_id=lga.lga_id,
                uniquewardid=ward.uniqueid,
                polling_unit_id=polling_unit_id,
            ).exists()
            if already_exists:
                self.add_error("polling_unit_id", "This polling unit ID already exists in the selected ward.")
        return data
