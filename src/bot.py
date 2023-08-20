import discord
from discord.interactions import Interaction
import random
import json

class Pack():
    def __init__(self, name: str, url: str, emoji: str, description: str) -> None:
        self.pack_name = name
        self.url = url
        self.emoji = emoji # Must be in ID format 
        self.description = description
        self.selected = False # Whether the player has selected the pack
    
    # What to return when str(Pack) is performed
    def __str__(self) -> str:
        return(
            "Pack Name: %s " \
            "Selected: %s\n" % (self.pack_name, self.selected)
        )
    
    # How to iterate over a list of Packs
    def __repr__(self):
        return str(self)
    
    # Convert from JSON to Pack
    @staticmethod
    def from_json(json_dct):
      return Pack(json_dct['pack_name'], json_dct['url'], json_dct['emoji'], json_dct['description'])

class Player():
    def __init__(self, name) -> None:
        self.name = name
        self.packs = []
    
    def __str__(self) -> str:
        return(
            "%s\n" % (self.name)
        )
    def __repr__(self):
        return str(self)

# Select Box, subclassed to allow access later
class PackSelect(discord.ui.Select):
    def __init__(self, packs, placeholder, disabled=False, next_sel=None, submit_button=None):
        self.packs = packs
        self.next_select = next_sel
        self.submit = submit_button
        options = [
            discord.SelectOption(
                label=self.packs[0].pack_name,
                emoji=self.packs[0].emoji,
                description=self.packs[0].description
            ),
            discord.SelectOption(
                label=self.packs[1].pack_name,
                emoji=self.packs[1].emoji,
                description=self.packs[1].description
            ),
            discord.SelectOption(
                label=self.packs[2].pack_name,
                emoji=self.packs[2].emoji,
                description=self.packs[2].description
            )
        ]

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            disabled=disabled,
            options=options)
    
    async def callback(self, interaction: Interaction): # Change the value of the selected pack to true on change and disable/enable controls
        pack = next((p for p in self.packs if p.pack_name == self.values[0]), None)
        pack.selected = True
        self.disabled = True
        option = next((o for o in self.options if o.label == self.values[0]), None)
        option.default=True # Set the default option to the selection to counteract reset
        
        if self.next_select:
            self.next_select.disabled = False
        if self.submit:
            self.submit.disabled = False
            
        await interaction.response.edit_message(view=self.view)
        #print(pack)

# Buttons subclassed to allow disabling later
class SubmitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Submit", 
            style=discord.ButtonStyle.success, 
            disabled=True
        )
    
    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.view.stop()

class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Cancel", 
            style=discord.ButtonStyle.danger
        )
    
    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        for p in self.player_packs: # Reset the packs to be deselected
            p.selected = False
        self.stop()

class PackSelectView(discord.ui.View):
    def __init__(self, player_packs):
        super().__init__()
        self.player_packs = player_packs
        self.cancelled = False # Whether the player cancelled the view
        
        # Initialize ui elements and add them to the view
        submit = SubmitButton()
        cancel = CancelButton()
        pack_select_2 = PackSelect(self.player_packs[3:], "Select Pack 2", True, submit_button=submit)
        pack_select_1 = PackSelect(self.player_packs[:3], "Select Pack 1", False, pack_select_2)
        self.add_item(pack_select_1)
        self.add_item(pack_select_2)
        self.add_item(submit)
        self.add_item(cancel)   

class JoinView(discord.ui.View):
    def __init__(self, time, packs, max_players, author, support_pack=None):
        super().__init__(timeout=time*60) # Set timeout
        self.time = time
        self.player_list = []
        self.pack_list = packs
        self.max_players = max_players
        self.author = author # User that started draft
        self.support_pack = support_pack

    async def on_timeout(self) -> None: # Callback for timeout
        self.disable_all_items() # Disable all ui components
        await self.message.edit(content="Timer expired, draft concluded.", view=self)
        return await super().on_timeout()
    
    # Create button with decorator, no need to access directly
    @discord.ui.button(label="Join Game!", style=discord.ButtonStyle.primary)
    async def join_callback(self, button, interaction):
        player = Player(interaction.user)
        for _ in range(6): # Select 6 packs at random for the player
            player.packs.append(self.pack_list.pop(random.randrange(0, len(self.pack_list))))
        self.player_list.append(player) 
        
        if len(self.player_list) == self.max_players:
            button.disabled = True
        
        embed = discord.Embed( # Create embed for welcome menu
            title="JumpStart Draft Manager",
            description="An automated method for pack selection.\n" + "",
            color=discord.Colour(0x7F00FF)
        )
        embed.add_field(
            name="**Game Rules**",
            value="1. Each player picks 1 pack out of 3 randomly distributed 24 card theme packs, twice. These are then shuffled with a 12 card support pack to form a 60 card sealed Commander deck.\n" +
            "2. Each pack has at least 2 commander options to choose from. Each is treated as if it had \"Partners with other packs.\"\n" +
            "3. Normal Commander rules apply.")
        embed.add_field(
            name="Participating",
            value=''.join([str(i) for i in self.player_list])
        )
        embed.add_field(
            name="Game Settings",
            value="Draft Runtime: " + str(self.time) + " minutes.\n" +
            "Number of Players: " + str(self.max_players) + "\n"
        )
        await interaction.response.defer(ephemeral=True) # Defer the response to allow for message editing before the response is sent, ephemeral = True allows it to be ephemeral in the future
        await interaction.edit_original_response(embed=embed) # Edit the original message to reflect players that joined
        #print(len(self.pack_list))
        view = PackSelectView(player.packs) # Instantiate view for pack selection
        eph_msg = await interaction.followup.send("### Choose two packs and then click Submit!", view=view, ephemeral=True) # Send the deferred response
        await view.wait() # Wait for the user to finish selecting packs or cancel
        
        if view.cancelled:
            self.player_list.remove(player)
            self.pack_list.extend(player.packs) # Add packs back to main pool
        else:
            player.packs.sort(key=lambda x: x.selected, reverse=True) # sort packs by selection status
            print(interaction.user.name + ": \n" + ''.join([str(i) for i in player.packs])) # Log selected packs
            self.pack_list.extend(player.packs[2:]) # Add back unselected packs
            player.packs = player.packs[:4] # Keep selected packs
        
        embed = discord.Embed( # Embed for final packs "view"
            title="JumpStart Draft Manager",
            description="Click the links below to view the pack lists. Follow the package creator on Moxfield to easily add packs to decklists.",
            color=discord.Colour(0x7F00FF)
        )
        embed.add_field(
            name="**Selected Packs**",
            value="[%s %s](%s)\n" % (player.packs[0].emoji, player.packs[0].pack_name, player.packs[0].url) +
                  "[%s %s](%s)" % (player.packs[1].emoji, player.packs[1].pack_name, player.packs[1].url)
            )
        if self.support_pack:
            embed.add_field(
                name="**Support Pack**",
                value="[%s %s](%s)\n" % (self.support_pack.emoji, self.support_pack.pack_name, self.support_pack.url)
            )
        await eph_msg.edit(content="", embed=embed, view=None) # Update the message
        # print(len(self.pack_list))
    
    @discord.ui.button(
        label="Start Game!",
        style=discord.ButtonStyle.success
    )
    async def start_callback(self, button, interaction):
        if self.author == interaction.user:
            await interaction.response.defer()
            self.disable_all_items()
            await interaction.edit_original_response(view=self)
            await interaction.followup.send("Draft concluded.")
        else:
            await interaction.response.send_message("Only the Draft creator may start the game early.", ephemeral=True)



class JumpStartManagerBot(discord.Bot):
    async def on_ready(self):
        self.pack_list = []
        self.support_pack = None

    async def start_draft(self, ctx, draft_timer, num_players):
        author = ctx.author
        print (len(self.pack_list))

        embed = discord.Embed(
            title="JumpStart Draft Manager",
            description="An automated method for pack selection.\n" + "",
            color=discord.Colour(0x7F00FF)
        )
        embed.add_field(
            name="**Game Rules**",
            value="1. Each player picks 1 pack out of 3 randomly distributed 24 card theme packs, twice. These are then shuffled with a 12 card support pack to form a 60 card sealed Commander deck.\n" +
            "2. Each pack has at least 2 commander options to choose from. Each is treated as if it had \"Partners with other packs.\"\n" +
            "3. Normal Commander rules apply.")
        embed.add_field(
            name="Participating",
            value="..."
        )
        embed.add_field(
            name="Game Settings",
            value="Draft Runtime: " + str(draft_timer) + " minutes.\n" +
            "Number of Players: " + str(num_players) + "\n"
        )
        if self.pack_list:
            await ctx.respond(embed=embed, view=JoinView(draft_timer, self.pack_list[:], num_players, author, support_pack=self.support_pack)) # Provides copy of pack list
        else:
            await ctx.respond("No pack list loaded.")
    
    # Load packs from CSV
    async def load_packs(self, ctx, csv_file):
        csv_file.pop(0)  # skip the headers
        for row in csv_file:
            #print(row.split(','))
            row = row.split(',')
            self.pack_list.append(Pack(row[0], row[1], row[2], row[3]))
        json_file = json.dumps([ob.__dict__ for ob in self.pack_list])
        print(json_file)
        with open('packs.json', 'w') as outfile:
            outfile.write(json_file)
        self.support_pack = self.pack_list.pop() # If not using support pack, comment this line out
        print(self.support_pack.pack_name)