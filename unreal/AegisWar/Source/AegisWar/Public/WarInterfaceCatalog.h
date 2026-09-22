#pragma once
#include "CoreMinimal.h"

class FJsonObject;
struct FWarMapMarker
{
    FString Id, Label, Layer;
    FVector2D Position = FVector2D::ZeroVector;
};
struct FWarMapZone
{
    FString Id, Name, Realm, Lane, Tier, Role;
    double Size = 800;
    TArray<FString> Destinations;
    TArray<TArray<FVector2D>> Paths;
    TArray<FWarMapMarker> Markers;
};
struct FWarGuidePage
{
    FString Id, Section, Title, Status, Text, SearchText;
};
struct AEGISWAR_API FWarInterfaceCatalog
{
    TArray<FWarMapZone> Zones;
    TArray<FWarGuidePage> Pages;
    TArray<TPair<FString, FString>> Sections;
    static FWarInterfaceCatalog Parse(const TSharedPtr<const FJsonObject>& Root);
    const FWarMapZone* FindZone(const FString& Id) const;
    TArray<int32> SearchGuide(const FString& Section, const FString& Query) const;
};
