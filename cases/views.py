from cases.models import CaseAssignment
from cases.models import Case
from django.shortcuts import redirect

def assign_juniors(request, case_id):
    case = Case.objects.get(id=case_id)

    if request.method == "POST":
        juniors = request.POST.getlist("juniors")
        responsibilities = request.POST.getlist("responsibilities")

        # clear old assignments
        CaseAssignment.objects.filter(case=case).delete()

        # create new ones
        for i in range(len(juniors)):
            CaseAssignment.objects.create(
                case=case,
                junior_id=juniors[i],
                responsibility=responsibilities[i]
            )

    return redirect("case_detail", case_id=case.id)