from calc.cosmetics import ActiveCosmetics
import statalib as lib
from statalib import to_thread
from statalib.render import (
    render_display_name,
    get_background,
    render_mc_text,
    image_to_bytes
)


@to_thread
def render_cosmetics(
    name: str,
    uuid: str,
    hypixel_data: dict
):
    cosmetics = ActiveCosmetics(name, hypixel_data)
    level = cosmetics.level
    rank_info = cosmetics.rank_info

    cosmetic_data = {
        'shopkeeper_skin': (299, 100),
        'projectile_trail': (299, 133),
        'death_cry': (299, 166),
        'wood_skin': (299, 199),
        'kill_effect': (299, 232),
        'island_topper': (299, 265),
        'victory_dance': (299, 298),
        'glyph': (299, 331),
        'spray': (299, 364),
        'bed_destroy': (299, 397),
        'kill_message': (299, 430)
    }

    image = get_background(
        bg_dir='cosmetics', uuid=uuid, level=level, rank_info=rank_info
    ).convert("RGBA")

    for cosmetic, (x, y) in cosmetic_data.items():
        text = getattr(cosmetics, cosmetic)

        render_mc_text(
            text=text,
            position=(x, y),
            font=lib.ASSET_LOADER.load_font("main.ttf", 16),
            image=image,
            shadow_offset=(2, 2)
        )

    render_display_name(
        username=name,
        rank_info=rank_info,
        level=level,
        image=image,
        font_size=20,
        position=(320, 51),
        align='center'
    )

    # Render the overlay image
    overlay_image = lib.ASSET_LOADER.load_image("bg/cosmetics/overlay.png")\
        .convert("RGBA")
    image.paste(overlay_image, (0, 0), overlay_image)

    return image_to_bytes(image)
