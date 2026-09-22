#pragma once
#include "CoreMinimal.h"

namespace WarActionBar
{
    inline constexpr int32 SlotCount = 10;
    inline FName Binding(int32 Slot) { return FName(*FString::Printf(TEXT("ActionSlot%d"), Slot + 1)); }
    inline bool IsSlotBinding(FName Action)
    {
        const FString Name = Action.ToString();
        const FString Number = Name.Mid(10);
        int32 Index = 0;
        return Name.StartsWith(TEXT("ActionSlot")) && LexTryParseString(Index, *Number) && Index > 0 && FString::FromInt(Index) == Number;
    }
    inline bool IsSupported(FName Action)
    {
        return Action.IsNone() || Action == TEXT("strike") || Action == TEXT("health_potion") || Action == TEXT("mana_potion");
    }
    inline FName Default(int32 Slot)
    {
        return Slot == 0 ? FName(TEXT("strike")) : Slot == 1 ? FName(TEXT("health_potion"))
            : Slot == 2 ? FName(TEXT("mana_potion")) : NAME_None;
    }
    inline FString Label(FName Action)
    {
        return Action == TEXT("strike") ? TEXT("Basic strike") : Action == TEXT("health_potion") ? TEXT("Health potion")
            : Action == TEXT("mana_potion") ? TEXT("Mana potion") : TEXT("Empty");
    }
}

struct FWarActionBarLayout
{
    int32 Id = 0;
    int32 Buttons = 10;
    FVector2D Position = FVector2D(0.5, 0.86);
    int32 Slot(int32 Button) const { return Id * WarActionBar::SlotCount + Button; }
};

struct FWarActionSlotView
{
    FString Label, Detail, Footer;
    float Cooldown = 0;
    int32 Count = 0;
    bool bAvailable = false;
};
