#pragma once
#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "WarActionBarRules.h"

struct FWarControlBinding { FName Action; FString Label; FKey Key; };
namespace WarControls
{
    inline TArray<FWarControlBinding> Defaults()
    {
        return {{TEXT("Forward"),TEXT("Move forward"),EKeys::W}, {TEXT("Backward"),TEXT("Move backward"),EKeys::S},
            {TEXT("Left"),TEXT("Strafe left"),EKeys::A}, {TEXT("Right"),TEXT("Strafe right"),EKeys::D},
            {TEXT("Jump"),TEXT("Jump"),EKeys::SpaceBar}, {TEXT("AutoRun"),TEXT("Auto-run"),EKeys::NumLock},
            {TEXT("Strike"),TEXT("Attack / left camera drag"),EKeys::LeftMouseButton},
            {TEXT("Orbit"),TEXT("Right camera drag"),EKeys::RightMouseButton},
            {TEXT("Interact"),TEXT("Interact / fly up"),EKeys::E}, {TEXT("FlyDown"),TEXT("Fly down"),EKeys::Q},
            {TEXT("Map"),TEXT("Map"),EKeys::M}, {TEXT("Character"),TEXT("Character"),EKeys::C},
            {TEXT("Inventory"),TEXT("Inventory"),EKeys::I}, {TEXT("Quests"),TEXT("Quest journal"),EKeys::L},
            {TEXT("Guide"),TEXT("How-to guide"),EKeys::H}, {TEXT("GM"),TEXT("GM tools"),EKeys::F2},
            {TEXT("Build"),TEXT("World builder"),EKeys::G},
            {TEXT("CycleTarget"),TEXT("Next hostile target"),EKeys::Tab},
            {TEXT("ActionCursor"),TEXT("Toggle action-bar cursor"),EKeys::V},
            {TEXT("ActionSlot1"),TEXT("Action slot 1"),EKeys::One},
            {TEXT("ActionSlot2"),TEXT("Action slot 2"),EKeys::Two},
            {TEXT("ActionSlot3"),TEXT("Action slot 3"),EKeys::Three},
            {TEXT("ActionSlot4"),TEXT("Action slot 4"),EKeys::Four},
            {TEXT("ActionSlot5"),TEXT("Action slot 5"),EKeys::Five},
            {TEXT("ActionSlot6"),TEXT("Action slot 6"),EKeys::Six},
            {TEXT("ActionSlot7"),TEXT("Action slot 7"),EKeys::Seven},
            {TEXT("ActionSlot8"),TEXT("Action slot 8"),EKeys::Eight},
            {TEXT("ActionSlot9"),TEXT("Action slot 9"),EKeys::Nine},
            {TEXT("ActionSlot10"),TEXT("Action slot 10"),EKeys::Zero}};
    }
    inline bool Validate(FName Action, FKey Key, const TMap<FName,FKey>& Bindings, FString& Error)
    {
        if (!WarActionBar::IsSlotBinding(Action) && !Defaults().ContainsByPredicate([Action](const auto& Entry){ return Entry.Action == Action; }))
        { Error=TEXT("Unknown action."); return false; }
        if (WarActionBar::IsSlotBinding(Action) && !Key.IsValid()) return true;
        if (!Key.IsValid() || Key.IsAxis1D() || Key.IsAxis2D() || Key.IsAxis3D() || Key.IsGamepadKey() || Key.IsModifierKey()
            || Key == EKeys::Escape || Key == EKeys::F1)
        { Error=TEXT("Choose a keyboard or mouse button. Escape and F1 are reserved."); return false; }
        for (const auto& Entry : Bindings) if (Entry.Key != Action && Entry.Value == Key)
        { Error=TEXT("That key is already assigned. Change the other action first."); return false; }
        return true;
    }
}
