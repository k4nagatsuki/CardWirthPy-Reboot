#!/usr/bin/env python
# -*- coding: utf-8 -*-

from string import Template


Adventurer = """$indent<Adventurer scaledimage="$scaledimage">
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePaths>$imgpaths
$indent  </ImagePaths>
$indent  <Description>$description</Description>
$indent  <Level>$level</Level>
$indent  <Life max="$maxlife">$life</Life>
$indent  <Feature>
$indent   <Type undead="$undead" automaton="$automaton" unholy="$unholy" constructure="$constructure" />
$indent   <NoEffect weapon="$noeffect_weapon" magic="$noeffect_magic" />
$indent   <Resist fire="$resist_fire" ice="$resist_ice" />
$indent   <Weakness fire="$weakness_fire" ice="$weakness_ice" />
$indent  </Feature>
$indent  <Ability>
$indent   <Physical dex="$dex" agl="$agl" int="$int" str="$str" vit="$vit" min="$min" />
$indent   <Mental aggressive="$aggressive" cheerful="$cheerful" brave="$brave" cautious="$cautious" trickish="$trickish" />
$indent   <Enhance avoid="$avoid" resist="$resist" defense="$defense" />
$indent  </Ability>
$indent  <Status>
$indent   <Mentality duration="$duration_mentality">$mentality</Mentality>
$indent   <Paralyze>$paralyze</Paralyze>
$indent   <Poison>$poison</Poison>
$indent   <Bind duration="$bind" />
$indent   <Silence duration="$silence" />
$indent   <FaceUp duration="$faceup" />
$indent   <AntiMagic duration="$antimagic" />
$indent  </Status>
$indent  <Enhance>
$indent   <Action duration="$duration_enhance_action">$enhance_action</Action>
$indent   <Avoid duration="$duration_enhance_avoid">$enhance_avoid</Avoid>
$indent   <Resist duration="$duration_enhance_resist">$enhance_resist</Resist>
$indent   <Defense duration="$duration_enhance_defense">$enhance_defense</Defense>
$indent  </Enhance>
$indent  <Coupons>$coupons
$indent  </Coupons>
$indent </Property>
$indent <ItemCards>$items
$indent </ItemCards>
$indent <SkillCards>$skills
$indent </SkillCards>
$indent <BeastCards>$beasts
$indent </BeastCards>
$indent</Adventurer>"""

ImagePath = """$indent<ImagePath positiontype="$postype">$path</ImagePath>"""

Album = """$indent<Album>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Level>$level</Level>
$indent  <Ability>
$indent   <Physical dex="$dex" agl="$agl" int="$int" str="$str" vit="$vit" min="$min" />
$indent   <Mental aggressive="$aggressive" cheerful="$cheerful" brave="$brave" cautious="$cautious" trickish="$trickish" />
$indent   <Enhance avoid="$avoid" resist="$resist" defense="$defense" />
$indent  </Ability>
$indent  <Coupons>$coupons
$indent  </Coupons>
$indent </Property>
$indent</Album>"""

Area = """$indent<Area>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent </Property>
$indent <BgImages>$bgimgs
$indent </BgImages>
$indent <MenuCards spreadtype="$spreadtype">$menucards
$indent </MenuCards>
$indent <Events>$events
$indent </Events>
$indent</Area>"""

Battle = """$indent<Battle>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <MusicPath>$bgm</MusicPath>
$indent </Property>
$indent <EnemyCards spreadtype="$spreadtype">$enemycards
$indent </EnemyCards>
$indent <Events>$events
$indent </Events>
$indent</Battle>"""

BeastCard = """$indent<BeastCard>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Scenario>$scenario</Scenario>
$indent  <Author>$author</Author>
$indent  <Ability physical="$p_ability" mental="$m_ability" />
$indent  <Target allrange="$target_all">$target</Target>
$indent  <EffectType spell="$silence">$effecttype</EffectType>
$indent  <ResistType>$resisttype</ResistType>
$indent  <SuccessRate>$successrate</SuccessRate>
$indent  <VisualEffect>$visual</VisualEffect>
$indent  <Enhance avoid="$enhance_avoid" resist="$enhance_resist" defense="$enhance_defense"/>
$indent  <SoundPath>$sound</SoundPath>
$indent  <SoundPath2>$sound2</SoundPath2>
$indent  <KeyCodes>$keycodes</KeyCodes>
$indent  <Premium>$premium</Premium>
$indent  <UseLimit>$uselimit</UseLimit>$attachment
$indent </Property>
$indent <Motions>$motions
$indent </Motions>
$indent <Events>$events
$indent </Events>
$indent</BeastCard>"""

CastCard = """$indent<CastCard>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Level>$level</Level>
$indent  <Money>$money</Money>
$indent  <Life max="$maxlife">$life</Life>
$indent  <Feature>
$indent   <Type undead="$undead" automaton="$automaton" unholy="$unholy" constructure="$constructure" />
$indent   <NoEffect weapon="$noeffect_weapon" magic="$noeffect_magic" />
$indent   <Resist fire="$resist_fire" ice="$resist_ice" />
$indent   <Weakness fire="$weakness_fire" ice="$weakness_ice" />
$indent  </Feature>
$indent  <Ability>
$indent   <Physical dex="$dex" agl="$agl" int="$int" str="$str" vit="$vit" min="$min" />
$indent   <Mental aggressive="$aggressive" cheerful="$cheerful" brave="$brave" cautious="$cautious" trickish="$trickish" />
$indent   <Enhance avoid="$avoid" resist="$resist" defense="$defense" />
$indent  </Ability>
$indent  <Status>
$indent   <Mentality duration="$duration_mentality">$mentality</Mentality>
$indent   <Paralyze>$paralyze</Paralyze>
$indent   <Poison>$poison</Poison>
$indent   <Bind duration="$bind" />
$indent   <Silence duration="$silence" />
$indent   <FaceUp duration="$faceup" />
$indent   <AntiMagic duration="$antimagic" />
$indent  </Status>
$indent  <Enhance>
$indent   <Action duration="$duration_enhance_action">$enhance_action</Action>
$indent   <Avoid duration="$duration_enhance_avoid">$enhance_avoid</Avoid>
$indent   <Resist duration="$duration_enhance_resist">$enhance_resist</Resist>
$indent   <Defense duration="$duration_enhance_defense">$enhance_defense</Defense>
$indent  </Enhance>
$indent  <Coupons>$coupons
$indent  </Coupons>
$indent </Property>
$indent <ItemCards>$items
$indent </ItemCards>
$indent <SkillCards>$skills
$indent </SkillCards>
$indent <BeastCards>$beasts
$indent </BeastCards>
$indent</CastCard>"""

Environment = """$indent<Environment>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <Skin>$skinname</Skin>
$indent  <Type>$skintype</Type>
$indent  <Cashbox>$cashbox</Cashbox>
$indent  <NowSelectingParty autoload="$is_autoloadparty">$selectingparty</NowSelectingParty>
$indent </Property>
$indent <CompleteStamps>$completestamps
$indent </CompleteStamps>
$indent <Gossips>$gossips
$indent </Gossips>
$indent</Environment>"""

InfoCard = """$indent<InfoCard>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent </Property>
$indent</InfoCard>"""

ItemCard = """$indent<ItemCard>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Scenario>$scenario</Scenario>
$indent  <Author>$author</Author>
$indent  <Ability physical="$p_ability" mental="$m_ability" />
$indent  <Target allrange="$target_all">$target</Target>
$indent  <EffectType spell="$silence">$effecttype</EffectType>
$indent  <ResistType>$resisttype</ResistType>
$indent  <SuccessRate>$successrate</SuccessRate>
$indent  <VisualEffect>$visual</VisualEffect>
$indent  <Enhance avoid="$enhance_avoid" resist="$enhance_resist" defense="$enhance_defense" />
$indent  <SoundPath>$sound</SoundPath>
$indent  <SoundPath2>$sound2</SoundPath2>
$indent  <KeyCodes>$keycodes</KeyCodes>
$indent  <Premium>$premium</Premium>
$indent  <UseLimit max="$uselimitmax">$uselimit</UseLimit>
$indent  <Price>$price</Price>
$indent  <EnhanceOwner avoid="$enhance_avoid2" resist="$enhance_resist2" defense="$enhance_defense2"/>
$indent  <Hold>$hold</Hold>
$indent </Property>
$indent <Motions>$motions
$indent </Motions>
$indent <Events>$events
$indent </Events>
$indent</ItemCard>"""

Package = """$indent<Package>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent </Property>
$indent <Events>$events
$indent </Events>
$indent</Package>"""

Party = """$indent<Party>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <Money>$money</Money>
$indent  <SuspendLevelUp>$suspend_levelup</SuspendLevelUp>
$indent  <Members>$members
$indent  </Members>
$indent </Property>
$indent <Backpack>$backpack
$indent </Backpack>
$indent</Party>"""

PartyRecord = """$indent<PartyRecord>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <Money>$money</Money>
$indent  <SuspendLevelUp>$suspend_levelup</SuspendLevelUp>
$indent  <Members>$members
$indent  </Members>
$indent </Property>
$indent <BackpackRecord>$backpack
$indent </BackpackRecord>
$indent</PartyRecord>"""

CardRecord = """$indent<CardRecord name="$name" desc="$desc" author="$author" scenario="$scenario" uselimit="$uselimit" />"""

SkillCard = """$indent<SkillCard>
$indent <Property>
$indent  <Id>$id</Id>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Scenario>$scenario</Scenario>
$indent  <Author>$author</Author>
$indent  <Level>$level</Level>
$indent  <Ability physical="$p_ability" mental="$m_ability" />
$indent  <Target allrange="$target_all">$target</Target>
$indent  <EffectType spell="$silence">$effecttype</EffectType>
$indent  <ResistType>$resisttype</ResistType>
$indent  <SuccessRate>$successrate</SuccessRate>
$indent  <VisualEffect>$visual</VisualEffect>
$indent  <Enhance avoid="$enhance_avoid" resist="$enhance_resist" defense="$enhance_defense"/>
$indent  <SoundPath>$sound</SoundPath>
$indent  <SoundPath2>$sound2</SoundPath2>
$indent  <KeyCodes>$keycodes</KeyCodes>
$indent  <Premium>$premium</Premium>
$indent  <UseLimit>$uselimit</UseLimit>
$indent  <Hold>$hold</Hold>
$indent </Property>
$indent <Motions>$motions
$indent </Motions>
$indent <Events>$events
$indent </Events>
$indent</SkillCard>"""

Summary = """$indent<Summary>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Author>$author</Author>
$indent  <Description>$description</Description>
$indent  <Level min="$levelmin" max="$levelmax" />
$indent  <RequiredCoupons number="$required_coupons_num">$required_coupons</RequiredCoupons>
$indent  <StartAreaId>$startarea_id</StartAreaId>
$indent  <Tags>$tags</Tags>
$indent  <Type>$skintype</Type>
$indent </Property>
$indent <Flags>$flags
$indent </Flags>
$indent <Steps>$steps
$indent </Steps>
$indent <Labels>$labels
$indent </Labels>
$indent</Summary>"""

BgImage = """$indent<BgImage mask="$mask">
$indent <ImagePath>$imgpath</ImagePath>
$indent <Flag>$flag</Flag>
$indent <Location left="$left" top="$top" />
$indent <Size width="$width" height="$height" />
$indent</BgImage>"""

Content = """$indent<$tag$type$name$properties>$children
$indent <Contents>$contents
$indent </Contents>
$indent</$tag>"""

Dialog = """$indent<Dialog>
$indent <RequiredCoupons>$coupons</RequiredCoupons>
$indent <Text>$text</Text>
$indent</Dialog>"""

Coupon = """$indent<Coupon value="$value">$name</Coupon>"""

EffectMotion = """$indent<Motion type="$type" element="$element"$properties$children"""

EnemyCard = """$indent<EnemyCard escape="$escape">
$indent <Property>
$indent  <Id>$castid</Id>
$indent  <Flag>$flag</Flag>
$indent  <Location left="$left" top="$top" />
$indent  <Size scale="$scale%" />
$indent </Property>
$indent <Events>$events
$indent </Events>
$indent</EnemyCard>"""

Event = """$indent<Event>
$indent <Ignitions>
$indent  <Number>$ignitions</Number>
$indent  <KeyCodes>$keycodes</KeyCodes>
$indent </Ignitions>
$indent <Contents>$contents
$indent </Contents>
$indent</Event>"""

Flag = """$indent<Flag default="$default">
$indent <Name>$name</Name>
$indent <True>$valname0</True>
$indent <False>$valname1</False>
$indent</Flag>"""

MenuCard = """$indent<MenuCard>
$indent <Property>
$indent  <Name>$name</Name>
$indent  <ImagePath>$imgpath</ImagePath>
$indent  <Description>$description</Description>
$indent  <Flag>$flag</Flag>
$indent  <Location left="$left" top="$top" />
$indent  <Size scale="$scale%" />
$indent </Property>
$indent <Events>$events
$indent </Events>
$indent</MenuCard>"""

SimpleEvent = """$indent<Event>
$indent <Contents>$contents
$indent </Contents>
$indent</Event>"""

Step = """$indent<Step default="$default">
$indent <Name>$name</Name>
$indent <Value0>$valname0</Value0>
$indent <Value1>$valname1</Value1>
$indent <Value2>$valname2</Value2>
$indent <Value3>$valname3</Value3>
$indent <Value4>$valname4</Value4>
$indent <Value5>$valname5</Value5>
$indent <Value6>$valname6</Value6>
$indent <Value7>$valname7</Value7>
$indent <Value8>$valname8</Value8>
$indent <Value9>$valname9</Value9>
$indent</Step>"""

def get_xmltemplate(name):
    return globals()[name]

def get_xmltext(name, d):
    s = get_xmltemplate(name)
    return Template(s).safe_substitute(d)

def main():
    pass

if __name__ == "__main__":
    main()
