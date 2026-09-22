#include "WarContentSubsystem.h"
#include "Dom/JsonObject.h"

FString UWarContentSubsystem::GetCampaignAtlasText() const
{
    const TArray<TSharedPtr<FJsonValue>>* Maps = nullptr;
    if (!Manifest || !Manifest->TryGetArrayField(TEXT("maps"), Maps)) return TEXT("Campaign catalog unavailable.");
    TMap<FString, FString> Names;
    for (const auto& Value : *Maps)
    {
        const auto Map = Value->AsObject();
        const TSharedPtr<FJsonObject>* Definition = nullptr;
        FString Id, Name;
        if (Map && Map->TryGetStringField(TEXT("id"), Id) && Map->TryGetObjectField(TEXT("definition"), Definition)
            && (*Definition)->TryGetStringField(TEXT("name"), Name)) Names.Add(Id, Name);
    }
    TArray<FString> Entries;
    for (const auto& Value : *Maps)
    {
        const auto Map = Value->AsObject();
        const TSharedPtr<FJsonObject>* Definition = nullptr;
        FString Id;
        if (!Map || !Map->TryGetStringField(TEXT("id"), Id) || !Map->TryGetObjectField(TEXT("definition"), Definition)) continue;
        TArray<FString> Destinations;
        const TArray<TSharedPtr<FJsonValue>>* Routes = nullptr;
        if ((*Definition)->TryGetArrayField(TEXT("zoneTriggers"), Routes))
            for (const auto& Route : *Routes)
            {
                FString Target;
                if (Route->AsObject() && Route->AsObject()->TryGetStringField(TEXT("targetZoneId"), Target))
                    Destinations.AddUnique(Names.Contains(Target) ? Names[Target] : Target);
            }
        Destinations.Sort();
        Entries.Add((Names.Contains(Id) ? Names[Id] : Id) + TEXT("\n    ") + FString::Join(Destinations, TEXT("  /  ")));
    }
    Entries.Sort();
    return FString::Join(Entries, TEXT("\n\n"));
}
