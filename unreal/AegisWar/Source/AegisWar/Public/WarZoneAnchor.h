#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerStart.h"
#include "WarZoneAnchor.generated.h"

/** A source zone's loaded bounds and collision-verified respawn point. */
UCLASS()
class AEGISWAR_API AWarZoneAnchor : public APlayerStart
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, Category="Zone") FName ZoneId;
    UPROPERTY(EditAnywhere, Category="Zone") FText ZoneName;
    UPROPERTY(EditAnywhere, Category="Zone") FVector ZoneOrigin = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Zone") double HalfSize = 60000;
    UPROPERTY(EditAnywhere, Category="Zone") bool bUseSpatialBounds = false;
    /** Native local XY centimetres, including owned backdrop scenery. */
    UPROPERTY(EditAnywhere, Category="Zone") FVector2D ContentMin = FVector2D(-60000,-60000);
    UPROPERTY(EditAnywhere, Category="Zone") FVector2D ContentMax = FVector2D(60000,60000);
    UPROPERTY(EditAnywhere, Category="Zone") TArray<FVector2D> PlayableOutline;
    /** Empty on legacy all-loaded maps; names resolve only against this world's authored streaming levels. */
    UPROPERTY(EditAnywhere, Category="Zone") TArray<FName> ContentLevels;
    UPROPERTY(EditAnywhere, Category="Zone") TObjectPtr<class UWarCityDefinition> CityDefinition;
    TArray<FName> GetContentLevels() const;
    bool ValidateCity(FString& Error) const;
    static bool ContainsPoint(FVector Origin, double Extent, FVector Point);
    bool ContainsOwnedPoint(FVector Point) const;
    bool ContainsPlayablePoint(FVector Point, double Margin = 0) const;
    bool ContainsPlayableSegment(FVector From, FVector To, double Margin = 0) const;
    static AWarZoneAnchor* FindAt(UWorld* World, FVector Point);
    static AWarZoneAnchor* FindById(UWorld* World, FName Id);
};
