#include "WarQuestMarkerRules.h"

EWarQuestMarker WarQuestMarkers::Resolve(const TArray<FWarQuestDefinition>& Definitions,
    const TArray<FWarQuestProgress>& Progress, FName Realm, FName Zone, FName Npc, int32 Level)
{
    if ((Realm != TEXT("aegis") && Realm != TEXT("riftbound")) || Zone.IsNone() || Npc.IsNone() || Level < 1)
        return EWarQuestMarker::None;
    bool bOffer = false;
    for (const auto& Quest : Definitions)
    {
        if (!Quest.Realm.IsNone() && Quest.Realm != Realm) continue;
        const auto* Own = Progress.FindByPredicate([&](const auto& Row) { return Row.Id == Quest.Id; });
        if (Quest.TurninNpcId == Npc && (Quest.TurninZoneId.IsNone() || Quest.TurninZoneId == Zone)
            && Own && Own->Status == TEXT("ready_to_turn_in")) return EWarQuestMarker::TurnIn;
        if (Quest.GiverNpcId != Npc) continue;
        auto Preview = Progress; FString Error;
        bOffer |= WarQuests::Accept(Quest, Realm, Zone, Level, Preview, Error);
    }
    return bOffer ? EWarQuestMarker::Offer : EWarQuestMarker::None;
}
