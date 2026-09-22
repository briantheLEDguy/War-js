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
    /** Empty on legacy all-loaded maps; names resolve only against this world's authored streaming levels. */
    UPROPERTY(EditAnywhere, Category="Zone") TArray<FName> ContentLevels;
    static bool ContainsPoint(FVector Origin, double Extent, FVector Point);
    static AWarZoneAnchor* FindAt(UWorld* World, FVector Point);
    static AWarZoneAnchor* FindById(UWorld* World, FName Id);
};
