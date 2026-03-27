#player_cards.py
try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


class PlayerCard:
    cards = []  # Stores all cards on initialization

    def __init__(self, card_id, player_name, position, season_year, stats, offensive_rating, defensive_rating, attributes, image_path):
        self.card_id = card_id
        self.player_name = player_name
        self.position = position
        self.season_year = season_year
        self.stats = stats
        self.offensive_rating = offensive_rating
        self.defensive_rating = defensive_rating
        self.attributes = attributes

        # Loads the image (optional: allow bot to run without PIL installed)
        if Image is None:
            self.image = None
        else:
            try:
                self.image = Image.open(image_path)  # Resize the image
                self.image = self.image.resize((200, 300))
                print(f"Image loaded successfully: {image_path}")
            except Exception as e:
                print(f"Error loading image: {e}")
                self.image = None  # Set image to None if loading fails

        PlayerCard.cards.append(self) # Add this card to the list of created cards

    @classmethod
    def get_cards(cls): # return full list of cards
        return cls.cards

    # player_cards.py
    @classmethod
    def get_card_by_name(cls, player_name):
        try:
            # Assuming the cards are stored in a list or database query
            for card in cls.cards:  # Adjust as needed for your card storage
                if card.get('player_name', '').lower() == player_name.lower():
                    return PlayerCard(card['player_name'], card['stats'])
            return None
        except Exception as e:
            print(f"Error retrieving card by player name: {e}")
            return None

    @classmethod
    def get_card_by_id(cls, card_id):
        """Retrieve a card by its ID."""
        for card in cls.cards:
            if card['id'] == card_id:
                return card
        return None

def initialize_player_cards():
    lebron_13 = PlayerCard(
        card_id=1,
        player_name="LeBron James",
        position = "Point Guard, Shooting Guard, Small Forward, Power Forward, Center",
        season_year="2012-2013",
        stats="PPG:26.8, RPG:8.0, APG:7.3, BPG:0.9, SPG:1.7",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\lebron13.png"
    )

    kd_14 = PlayerCard(
        card_id=2,
        player_name="Kevin Durant",
        position="Small Forward, Power Forward",
        season_year="2013-2014",
        stats="PPG:32.0, RPG:7.4, APG:5.5, BPG:0.7, SPG:1.3",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\kd14.png"
    )

    curry_16 = PlayerCard(
        card_id=3,
        player_name="Stephen Curry",
        position="Point Guard, Shooting Guard",
        season_year="2015-2016",
        stats="PPG:30.1, RPG:5.4, APG:6.7, BPG:0.2, SPG:2.1",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\curry16.png"
    )

    westbrook_17 = PlayerCard(
        card_id=4,
        player_name="Russell Westbrook",
        position="Point Guard, Shooting Guard",
        season_year="2016-2017",
        stats="PPG:31.6, RPG:10.7, APG:10.4, BPG:0.4, SPG:1.6",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\westbrook17.png"
    )

    kobe_06 = PlayerCard(
        card_id=5,
        player_name="Kobe Bryant",
        position="Shooting Guard, Small Forward",
        season_year="2005-2006",
        stats="PPG:35.4, RPG:5.3, APG:4.5, BPG:0.4, SPG:1.8",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\kobe06.png"
    )

    mj_96 = PlayerCard(
        card_id=6,
        player_name="Michael Jordan",
        position="Shooting Guard, Small Forward",
        season_year="1995-1996",
        stats="PPG:30.4, RPG:6.6, APG:4.3, BPG:0.5, SPG:2.2",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\mj96.png"
    )

    shaq_01 = PlayerCard(
        card_id=7,
        player_name="Shaquille O'Neal",
        position="Power Forward, Center",
        season_year="2000-2001",
        stats="PPG:28.7, RPG:12.7, APG:3.7, BPG:2.8, SPG:0.6",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\shaq01.png"
    )

    duncan_03 = PlayerCard(
        card_id=8,
        player_name="Tim Duncan",
        position="Power Forward, Center",
        season_year="2002-2003",
        stats="PPG:23.3, RPG:12.9, APG:3.9, BPG:2.9, SPG:0.7",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\duncan03.png"
    )

    garnett_04 = PlayerCard(
        card_id=9,
        player_name="Kevin Garnett",
        position="Small Forward, Power Forward, Center",
        season_year="2003-2004",
        stats="PPG:24.2, RPG:13.9, APG:5.0, BPG:2.2, SPG:1.5",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\garnett04.png"
    )

    harden_18 = PlayerCard(
        card_id=10,
        player_name="James Harden",
        position="Point Guard, Shooting Guard",
        season_year="2017-2018",
        stats="PPG:30.4, RPG:5.4, APG:8.8, BPG:0.7, SPG:1.8",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\harden18.png"
    )

    giannis_20 = PlayerCard(
        card_id=11,
        player_name="Giannis Antetokounmpo",
        position="Power Forward, Center",
        season_year="2019-2020",
        stats="PPG:29.5, RPG:13.6, APG:5.6, BPG:1.0, SPG:1.0",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\giannis20.png"
    )

    bird_86 = PlayerCard(
        card_id=12,
        player_name="Larry Bird",
        position="Small Forward, Power Forward",
        season_year="1985-1986",
        stats="PPG:25.8, RPG:9.8, APG:6.8, BPG:0.6, SPG:2.0",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\bird86.png"
    )

    magic_87 = PlayerCard(
        card_id=13,
        player_name="Magic Johnson",
        position="Point Guard, Power Forward, Center",
        season_year="1986-1987",
        stats="PPG:23.9, RPG:6.3, APG:12.2, BPG:0.5, SPG:1.7",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\magic87.png"
    )

    dirk_11 = PlayerCard(
        card_id=14,
        player_name="Dirk Nowitzki",
        position="Power Forward, Center",
        season_year="2010-2011",
        stats="PPG:23.0, RPG:7.0, APG:2.6, BPG:0.6, SPG:0.5",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\dirk11.png"
    )

    ai_01 = PlayerCard(
        card_id=15,
        player_name="Allen Iverson",
        position="Point Guard, Shooting Guard",
        season_year="2000-2001",
        stats="PPG:31.1, RPG:3.8, APG:4.6, BPG:0.3, SPG:2.5",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\ai01.png"
    )

    cp3_14 = PlayerCard(
        card_id=16,
        player_name="Chris Paul",
        position="Point Guard",
        season_year="2013-2014",
        stats="PPG:19.1, RPG:4.3, APG:10.7, BPG:0.1, SPG:2.5",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\cp3_14.png"
    )

    kawhi_15 = PlayerCard(
        card_id=17,
        player_name="Kawhi Leonard",
        position="Small Forward, Power Foward",
        season_year="2014-2015",
        stats="PPG:16.5, RPG:7.2, APG:2.5, BPG:0.8, SPG:2.3",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\kawhi15.png"
    )

    nash_06 = PlayerCard(
        card_id=18,
        player_name="Steve Nash",
        position="Point Guard",
        season_year="2005-2006",
        stats="PPG:18.8, RPG:4.2, APG:10.5, BPG:0.2, SPG:0.8",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\nash06.png"
    )

    davis_20 = PlayerCard(
        card_id=19,
        player_name="Anthony Davis",
        position="Power Forward, Center",
        season_year="2019-2020",
        stats="PPG:26.1, RPG:9.3, APG:3.2, BPG:2.3, SPG:1.5",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\davis20.png"
    )

    embiid_22 = PlayerCard(
        card_id=20,
        player_name="Joel Embiid",
        position="Power Forward, Center",
        season_year="2021-2022",
        stats="PPG:30.6, RPG:11.7, APG:4.2, BPG:1.5, SPG:1.1",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\embiid22.png"
    )

    jokic_21 = PlayerCard(
        card_id=21,
        player_name="Nikola Jokić",
        position="Power Forward, Center",
        season_year="2020-2021",
        stats="PPG:26.4, RPG:10.8, APG:8.3, BPG:0.7, SPG:1.3",
        offensive_rating=94,
        defensive_rating=90,
        attributes=['x'],
        image_path=r"C:\Users\brace\Downloads\cards\jokic21.png"
    )
