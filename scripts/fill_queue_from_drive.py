#!/usr/bin/env python3
"""
fill_queue_from_drive.py — Populate Google Sheets queue from Drive folder scenarios.

Reads scenario documents discovered in Drive folder 1LLH-iRTNMd3NtfnkLyA8row4J0IhQiBp
and adds structured queue entries.

Status guide:
  pending  — existing generator, ready to render immediately
  planned  — needs new Remotion composition first (tracked but not auto-dispatched)
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET_ID = '1MAHh_LxESZCd0sWOx0qAjSWWIElR79oTfo-XiPbJc7o'
KEY_FILE = ROOT / 'credentials' / 'drive_service_account.json'
SCOPES   = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly',
]
TAB = 'Queue'

# Column order matches sheet header
COL_ORDER = ['id','type','lang','key','doc_url','params','priority','status',
             'youtube_id_en','youtube_id_ar','notes','created','updated']

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

def doc_url(doc_id):
    return f'https://docs.google.com/document/d/{doc_id}'

def get_creds():
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(str(KEY_FILE), scopes=SCOPES)

def get_svc():
    from googleapiclient.discovery import build
    return build('sheets', 'v4', credentials=get_creds()).spreadsheets()

def read_existing_queue(svc):
    result = svc.values().get(spreadsheetId=SHEET_ID, range=f'{TAB}!A2:M200').execute()
    return result.get('values', [])

def append_rows(svc, rows):
    svc.values().append(
        spreadsheetId=SHEET_ID,
        range=f'{TAB}!A2',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def main():
    svc = get_svc()
    existing = read_existing_queue(svc)

    existing_ids  = {r[0] for r in existing if r}
    existing_keys = {(r[1], r[3]) for r in existing if len(r) > 3}  # (type, key)

    print(f"Existing rows: {len(existing)}")
    print(f"Existing keys: {existing_keys}")

    ts = now_iso()

    # ── All scenarios from Drive folder ────────────────────────────────────────
    # (id, type, lang, key, doc_url, params, priority, status, notes)
    scenarios = [

        # ══ INDONESIAN NURSERY SONGS ══════════════════════════════════════════
        # 6 full-script videos — need NurserySongID Remotion composition
        # Kling AI reference images in Drive folder

        (4,  'nursery_id', 'id', 'balonku',
         doc_url('1hHT1dyti8MzWtxWi-NSuRKLFYaPRbYj9NYlWGE1gS_I'),
         'duration=20', 11, 'planned',
         'Balonku Ada Lima — Indonesian balloon song. NEEDS: NurserySongID Remotion. Kling AI images in Drive.'),

        (5,  'nursery_id', 'id', 'cicak',
         doc_url('1lcShtapwuWRVx5nZKqs3fa8N_TlYcGnNJbwdROvOdyY'),
         'duration=20', 12, 'planned',
         'Cicak-Cicak di Dinding — Indonesian lizard-on-wall song. NEEDS: NurserySongID Remotion.'),

        (6,  'nursery_id', 'id', 'naik_kereta',
         doc_url('1uZ2uup5PjbHrZHHHcCKG98b2AQv3yLSkxRlT9e2kTeo'),
         'duration=20', 13, 'planned',
         'Naik Kereta Api — Indonesian train song. NEEDS: NurserySongID Remotion.'),

        (7,  'nursery_id', 'id', 'pelangi',
         doc_url('11LV7YtG3wlJEhVQkuhdSBAeugjXs8-p5JWUP8UCBFO4'),
         'duration=20', 14, 'planned',
         'Pelangi-Pelangi — Indonesian rainbow song. NEEDS: NurserySongID Remotion.'),

        (8,  'nursery_id', 'id', 'dua_mata',
         doc_url('1ZEPOqdpsPjRsYkjlHMx_hD_suLy5j2hk3MhjaF08vyQ'),
         'duration=20', 15, 'planned',
         'Dua Mata Saya — Indonesian body parts song. NEEDS: NurserySongID Remotion.'),

        (9,  'nursery_id', 'id', 'kebunku',
         doc_url('1oIY2INGvWZ05tQZ7hkG6ScJ4IoT46eEijOKdP5gEScw'),
         'duration=20', 16, 'planned',
         'Kebunku — Indonesian garden song. NEEDS: NurserySongID Remotion.'),

        # ══ ARABIC NURSERY SONGS ══════════════════════════════════════════════
        # 3 full-script videos — need NurserySongAR Remotion composition

        (10, 'nursery_ar', 'ar', 'batta_batta',
         doc_url('1MSKfq670CN-gcYZ-9DNm45eCNgxA2gQVDWiQIE5g1ws'),
         'duration=20', 21, 'planned',
         'بتة بتة Batta Batta — Arabic duck song. NEEDS: NurserySongAR Remotion.'),

        (11, 'nursery_ar', 'ar', 'ya_matar',
         doc_url('1qaEqvUkGgKdXZup6KlwHGa4-IMgRbTdS_KHUFUkZRZ8'),
         'duration=20', 22, 'planned',
         'يا مطر Ya Matar — Arabic rain song. NEEDS: NurserySongAR Remotion.'),

        (12, 'nursery_ar', 'ar', 'dajaja',
         doc_url('1PmbQnBPFcJ8HBUnVbiOMw9x-cTD4R_rFql3cxv9keI4'),
         'duration=20', 23, 'planned',
         'دجاجة Dajaja — Arabic chicken song. NEEDS: NurserySongAR Remotion.'),

        # ══ SENSORY LOOP VIDEOS (14 total) ════════════════════════════════════
        # Pure visual loops, no words, ages 0-12 months

        (13, 'sensory_loop', 'both', 'sensory_1_3',
         doc_url('1c5Gqe9aFLsuGgUajJKEteA2IyoD9jI4fAKjZ1dUIQ6o'),
         'episodes=3,duration=30', 31, 'planned',
         'Sensory Videos 1-3 — from Production Plan doc. NEEDS: SensoryLoop Remotion composition.'),

        (14, 'sensory_loop', 'both', 'sensory_4_14',
         doc_url('1T6-4Y2oShOaTKYEehhQtV00z-sC_DiFNV7Fn25R1myU'),
         'episodes=11,duration=30', 32, 'planned',
         'Sensory Videos 4-14 — Falling Stars, Bubbles, Color Wash, etc. NEEDS: SensoryLoop Remotion.'),

        # ══ STARS AND BUBBLES ═════════════════════════════════════════════════
        (15, 'stars_bubbles', 'en', 'stars_bubbles',
         doc_url('1pUJcGfvE3aGUIk7V9uZJyVg1vHmiLnN_mv_oxnrfgNI'),
         'duration=22', 33, 'planned',
         'Stars & Bubbles — 22 min EN. POP sound design = 70% of experience. NEEDS: StarsBubbles Remotion.'),

        # ══ DANCING SHAPES SERIES (12 videos × 25 min, no words) ═════════════
        (16, 'dance_shape', 'both', 'dance_shapes_series',
         doc_url('1JkLrFKaQI64eVCNsjIQ2oX6m301V_y63w_bVwxWPomY'),
         'episodes=12,duration=25', 41, 'planned',
         '12 shapes × 25 min no-words. BOB/SWAY/SPIN/DRIFT/PULSE movements. NEEDS: DanceShape Remotion composition.'),

        # ══ DANCING PETS SERIES (33 videos) ══════════════════════════════════
        # 10 animals × A (no words 25min) + B (group) + C (learn) = 33 videos
        (17, 'dance_pet', 'both', 'dance_pets_series',
         doc_url('12VmquGoRPEYhgImncEPG5JlCMuGWvKBB_9LqZicV4wg'),
         'episodes=33,duration=25', 51, 'planned',
         '33 videos: cat/dog/rabbit/fish/turtle/parrot/hamster/guinea_pig/duck/kitten. A=solo 25min, B=group, C=learn. NEEDS: DancePet Remotion. Meshy GLB models in Drive.'),

        # ══ DANCING HOUSEHOLD ITEMS (25 videos) ══════════════════════════════
        (18, 'dance_item', 'both', 'dance_items_series',
         doc_url('12ibdhe_pQ2MOJrcU4iEjdcysFVL-lh0KyNuMuIlZ1Dw'),
         'episodes=25,duration=25', 61, 'planned',
         '25 items: mug/spoon/plate/kettle/ball/cube/pyramid/rattle/shoe etc. A=no words, B=learn. NEEDS: DanceItem Remotion.'),

        # ══ LULLABY LONG-FORM (1-2 hour sleep content) ═══════════════════════
        (19, 'lullaby_long', 'both', 'lullaby_nature',
         doc_url('1lW2CXmlq1lhzZ7cex5qHmCuAVo_mVjzahIwOOy7E3Jo'),
         'duration=120', 71, 'planned',
         '1-2hr sleep content. 5-min Remotion loop × FFmpeg. Brightness fades to 40% by 1hr. ≤55 BPM. NEEDS: LullabyLong Remotion.'),

        # ══ TRANSFORMATION BLOCKS (5 blocks × 4 videos = 20 videos) ══════════

        (20, 'transform_block', 'both', 'transform_1_fruits',
         doc_url('1vK0zO4n4Pfy_3EPLAB7y0G7WlKcMz0Kkn_yPGTx2PlE'),
         'block=1,episodes=4', 81, 'planned',
         'Block 1 - Transformations: fruit grows seed→tree→fruit→fall→seed. 4 videos. NEEDS: TransformBlock Remotion.'),

        (21, 'transform_block', 'both', 'transform_2_color',
         doc_url('1p7HGXBwhZvhIR-C_Ziw9TvQoHTHrNA5ecrzfl55h3O4'),
         'block=2,episodes=4', 82, 'planned',
         'Block 2 - Color as main character. 4 videos. NEEDS: TransformBlock Remotion.'),

        (22, 'transform_block', 'both', 'transform_3_physics',
         doc_url('1tmyu8wfqSRsxExg-zHy8eHReqU-0yH5l78An1R0fth0'),
         'block=3,episodes=4', 83, 'planned',
         'Block 3 - Physical phenomena: bouncing/physics fruits. 4 videos. NEEDS: TransformBlock Remotion.'),

        (23, 'transform_block', 'both', 'transform_4_patterns',
         doc_url('1EyH1moaTTZOxP6-NWb4IRU7ra1JgVXvAyoxB0snFqeY'),
         'block=4,episodes=4', 84, 'planned',
         'Block 4 - Patterns & symmetry. 4 videos. NEEDS: TransformBlock Remotion.'),

        (24, 'transform_block', 'both', 'transform_5_nature',
         doc_url('1y9525GrfLnSctoNicOxSQ9NxRD1kjuw1JP6CU3902rI'),
         'block=5,episodes=4', 85, 'planned',
         'Block 5 - Natural cycles. 4 videos. NEEDS: TransformBlock Remotion.'),

        # ══ GROUP DANCES FRUITS & VEGETABLES (8 videos) ═══════════════════════
        (25, 'dance_fruits_group', 'both', 'fruits_veg_group_8',
         doc_url('1lIGDQ0bHs8277Z1un-O_tNwOWRi4fusu4mUAtnt9fmk'),
         'episodes=8,duration=25', 91, 'planned',
         '8 group dance videos × 25-30 min. Color family groupings. Reuses dance pipeline sprites. NEEDS: DanceFruitsGroup Remotion.'),

        # ══ DANCING FRUITS/VEGE TWO-STAGE SERIES ══════════════════════════════
        (26, 'dance_fruits_2stage', 'both', 'fruits_veg_2stage',
         doc_url('1_VP163cpfsLmhPXZtRH7Jjn4wulXYRfcXRX4cSU0Uos'),
         '', 92, 'planned',
         'Two-stage: Stage 1 no-words (visual intro), Stage 2 text+voice (learning). Reuses existing sprites. NEEDS: 2-stage Remotion comp.'),

        # ══ LEARN TO TALK (Ms Rachel style) ═══════════════════════════════════
        (27, 'learn_to_talk', 'en', 'learn_to_talk_series',
         doc_url('1T1SGUAdmLHzaQPrUq-EzT0St-30lvaQlOcJs2pLmbqo'),
         '', 101, 'planned',
         'Ms Rachel style speech development series. EN only. NEEDS: LearnToTalk Remotion composition.'),

        # ══ EMOTIONS + OCEAN + TRANSPORT + PROFESSIONS ════════════════════════
        (28, 'emotions_ocean', 'both', 'emotions_4series',
         doc_url('1LXJJYJ1qiN94FeQAP8lCzbY2WDm_vVlVkyk3cZEWDmo'),
         'series=4', 111, 'planned',
         '4 series: Emotions / Ocean / Transport / Professions. NEEDS: separate Remotion compositions per topic.'),

        # ══ SPECIAL MECHANICS (8 series, A no-words + B EN+AR) ════════════════
        (29, 'special_mechanics', 'both', 'special_mech_8series',
         doc_url('1uM63tCo83niXy_AH7I0NXsc6Hoenv_n8OSBFD5iIwAM'),
         'series=8', 121, 'planned',
         '8 special mechanic series incl. Hide & Seek (most powerful child hook). A=no words, B=EN+AR. NEEDS: SpecialMechanics Remotion.'),

        # ══ SHAPE ROUNDELAY ═══════════════════════════════════════════════════
        (30, 'shape_roundelay', 'both', 'shape_roundelay',
         doc_url('1r7EdP3iI5fWyBu3osW8qsmwxbFzfExcyTlIrrEH_qFM'),
         '', 131, 'planned',
         'Shapes dancing in a round, satisfying loops. NEEDS: ShapeRoundelay Remotion.'),

        # ══ VEHICLES ONE CONCEPT DEEP ═════════════════════════════════════════
        (31, 'ocd_vehicles', 'both', 'vehicles_ocd_series',
         doc_url('17TRPr0UtPwgqOznjxVYsRQCvvM_sdpohrRlDtbT9Zro'),
         '', 141, 'planned',
         'Vehicles OCD series: trucks, excavators, trains etc. NEEDS: OCDVehicles Remotion.'),

        # ══ CONSTRUCTION + WORLD INSTRUMENTS ═════════════════════════════════
        (32, 'construction_music', 'both', 'construction_instruments',
         doc_url('185vTemW9PLxgmzpeZUHi_OTdtkLNSomSi-0LSOji2tE'),
         '', 151, 'planned',
         'Building tools + world musical instruments two-topic series. NEEDS: new Remotion.'),

        # ══ BUBBLE POP ORIGINAL SONG ══════════════════════════════════════════
        (33, 'bubble_pop_song', 'en', 'bubble_pop',
         doc_url('1IAdVxLs2osioTyevT4yGrv8EWBtuaw4-kfQLI2YrE_o'),
         '', 161, 'planned',
         'Original channel hit song BUBBLE POP. EN. NEEDS: BubblePop Remotion with song integration.'),

        # ══ THREE HIGH-WATCH-TIME FORMATS ════════════════════════════════════
        (34, 'satisfying_3fmt', 'both', 'satisfying_guess_surprise',
         doc_url('1xqT_1GXyWrY_OjsZQnH3lQJ85HkLzea7plGePzqgEJQ'),
         'formats=3', 171, 'planned',
         '3 high-retention formats: Satisfying loops / Guess the Sound / Surprise Reveal. NEEDS: 3 Remotion compositions.'),

        # ══ CALM NATURE SCENARIOS (Category 2) ═══════════════════════════════
        (35, 'nature_calm', 'both', 'nature_calm_cat2',
         doc_url('196whGbWzmYjp0AOLAxvErPSvnotuT3PIf5MjqU_Gp-g'),
         '', 181, 'planned',
         'Calm nature background videos. Category 2. NEEDS: NatureCalm Remotion.'),

        # ══ INTERACTIVE CO-VIEWING (Category 3) ══════════════════════════════
        (36, 'interactive_coview', 'both', 'coview_cat3',
         doc_url('1LITeHcxsthOot8a1Gfg86fP7Ivrk67Yi-WNn34NI0vY'),
         '', 191, 'planned',
         'Interactive co-viewing: parent+child activities. Category 3. NEEDS: Interactive Remotion.'),

        # ══ EMOTIONAL SCENARIOS WITH VALUES (Category 4) ════════════════════
        (37, 'emotional_values', 'both', 'emotions_values_cat4',
         doc_url('1IlaCEHkMTdqjTMUzDJTrPjIdmjOCA5aQxgy00adSuIc'),
         '', 201, 'planned',
         'Empathy/values educational content. Category 4. NEEDS: EmotionalValues Remotion.'),

        # ══ SHORTS FUNNEL FROM EXISTING LONG VIDEOS ══════════════════════════
        (38, 'shorts_funnel', 'both', 'shorts_from_long',
         doc_url('1bQqfwCUkNormV3qt4Y29hFA0-uC-dtc4CJy7iY9W2Lw'),
         '', 211, 'planned',
         'Strategy: cut 60-sec Shorts from existing long videos. No render needed — just clip selection & upload. See doc.'),

        # ══ EDUCATIONAL-ENTERTAINMENT SCENARIOS (Category 1) ════════════════
        (39, 'edu_entertain', 'both', 'edu_entertain_cat1',
         doc_url('1xeMaTsNTeT7KPrSUQPdGfoT_PcbwU2M-9obyinxP39o'),
         '', 221, 'planned',
         'Educational-entertainment hybrid scenarios. Category 1. NEEDS: EduEntertain Remotion.'),
    ]

    # ── Filter out already-existing entries ────────────────────────────────────
    to_add = []
    for s in scenarios:
        sid, stype, slang, skey = str(s[0]), s[1], s[2], s[3]
        if sid in existing_ids:
            print(f"  SKIP (id exists): {sid} {stype}/{skey}")
            continue
        if (stype, skey) in existing_keys:
            print(f"  SKIP (type+key exists): {stype}/{skey}")
            continue
        to_add.append(s)

    if not to_add:
        print("Nothing new to add.")
        return

    print(f"\nAdding {len(to_add)} new rows...")

    rows = []
    for s in to_add:
        sid, stype, slang, skey, sdoc, sparams, spri, sstatus, snotes = s
        rows.append([
            str(sid),   # id
            stype,      # type
            slang,      # lang
            skey,       # key
            sdoc,       # doc_url
            sparams,    # params
            str(spri),  # priority
            sstatus,    # status
            '',         # youtube_id_en
            '',         # youtube_id_ar
            snotes,     # notes
            ts,         # created
            ts,         # updated
        ])

    append_rows(svc, rows)
    print(f"✓ Added {len(rows)} rows to queue.")
    for r in rows:
        print(f"  [{r[6]:>3}] {r[0]:>3} | {r[1]:<22} | {r[3]:<28} | {r[7]}")


if __name__ == '__main__':
    main()
