from django.db import migrations


SAMPLE_MATERIALS = [
    {
        "title": "Quadratic equations, made clear",
        "subject": "Mathematics",
        "class_level": "Class 10",
        "description": "Understand the standard form, discriminant and quadratic formula with a simple worked example.",
        "price": "129.00",
        "cover_image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=900&q=80",
        "notes_content": (
            "QUADRATIC EQUATIONS\n\n"
            "A quadratic equation has the form ax^2 + bx + c = 0, where a is not zero.\n\n"
            "WAYS TO SOLVE\n"
            "1. Factorise the expression when it can be written as a product of two linear factors.\n"
            "2. Complete the square to rewrite the equation as a squared expression equal to a constant.\n"
            "3. Use the quadratic formula: x = (-b +/- sqrt(b^2 - 4ac)) / 2a.\n\n"
            "THE DISCRIMINANT\n"
            "D = b^2 - 4ac. If D is positive there are two distinct real roots; if D is zero "
            "there is one repeated real root; if D is negative there are no real roots.\n\n"
            "QUICK CHECK\n"
            "For x^2 - 5x + 6 = 0, factorise to (x - 2)(x - 3) = 0. The roots are 2 and 3."
        ),
    },
    {
        "title": "Motion: speed, velocity & acceleration",
        "subject": "Physics",
        "class_level": "Class 9",
        "description": "A quick, clear guide to distance, displacement, speed, velocity and motion graphs.",
        "price": "99.00",
        "cover_image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80",
        "notes_content": (
            "MOTION - KEY IDEAS\n\n"
            "Distance is the total path travelled. Displacement is the straight-line change "
            "from the starting point to the finishing point, with direction.\n\n"
            "Speed = distance / time. Average speed uses the total distance and total time.\n"
            "Velocity = displacement / time and includes direction.\n"
            "Acceleration = (final velocity - initial velocity) / time.\n\n"
            "UNITS\n"
            "Distance: metre (m) | Time: second (s) | Speed and velocity: m/s | "
            "Acceleration: m/s^2\n\n"
            "MOTION GRAPHS\n"
            "The slope of a distance-time graph gives speed. The slope of a velocity-time "
            "graph gives acceleration. The area under a velocity-time graph gives displacement.\n\n"
            "Remember: an object can travel a non-zero distance and still have zero "
            "displacement if it returns to its starting point."
        ),
    },
    {
        "title": "The cell: structure & function",
        "subject": "Biology",
        "class_level": "Class 9",
        "description": "Explore cell organelles and how plant and animal cells are organised.",
        "price": "109.00",
        "cover_image": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=900&q=80",
        "notes_content": (
            "THE CELL\n\n"
            "The cell is the basic structural and functional unit of life. The cell membrane "
            "surrounds the cell and controls what enters and leaves it.\n\n"
            "IMPORTANT ORGANELLES\n"
            "Nucleus: contains genetic material and helps control cell activities.\n"
            "Cytoplasm: jelly-like material where many chemical reactions take place.\n"
            "Mitochondria: release energy during cellular respiration.\n"
            "Vacuole: stores water and other substances; usually large in plant cells.\n"
            "Chloroplast: contains chlorophyll and is the site of photosynthesis in plant cells.\n\n"
            "PLANT AND ANIMAL CELLS\n"
            "Plant cells have a cellulose cell wall, chloroplasts and usually a large central "
            "vacuole. Animal cells do not have a cell wall or chloroplasts.\n\n"
            "A helpful way to remember it: the membrane is the boundary, the nucleus is the "
            "control centre, and mitochondria provide usable energy."
        ),
    },
    {
        "title": "Chemical reactions & equations",
        "subject": "Chemistry",
        "class_level": "Class 10",
        "description": "Recognise common reaction types and learn to balance chemical equations.",
        "price": "119.00",
        "cover_image": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=900&q=80",
        "notes_content": (
            "CHEMICAL REACTIONS\n\n"
            "A chemical reaction rearranges atoms to form new substances. A chemical equation "
            "represents reactants on the left and products on the right.\n\n"
            "BALANCING EQUATIONS\n"
            "The number of atoms of each element must be the same on both sides. Change "
            "coefficients in front of formulas; never change the small numbers inside a formula.\n\n"
            "Example: H2 + O2 -> H2O becomes 2H2 + O2 -> 2H2O.\n\n"
            "COMMON REACTION TYPES\n"
            "Combination: two or more reactants form one product.\n"
            "Decomposition: one compound breaks into simpler substances.\n"
            "Displacement: a more reactive element replaces a less reactive one.\n"
            "Oxidation: gain of oxygen or loss of hydrogen. Reduction is the opposite.\n\n"
            "Always count each kind of atom on both sides to check your final equation."
        ),
    },
]


def add_sample_materials(apps, schema_editor):
    StudyMaterial = apps.get_model("material_provider", "StudyMaterial")
    for material in SAMPLE_MATERIALS:
        StudyMaterial.objects.get_or_create(
            title=material["title"],
            defaults=material,
        )


def remove_sample_materials(apps, schema_editor):
    StudyMaterial = apps.get_model("material_provider", "StudyMaterial")
    StudyMaterial.objects.filter(
        title__in=[material["title"] for material in SAMPLE_MATERIALS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("material_provider", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_sample_materials, remove_sample_materials),
    ]
