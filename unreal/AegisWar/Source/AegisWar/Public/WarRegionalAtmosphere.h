#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarRegionalAtmosphere.generated.h"

class UProceduralMeshComponent;
class UAudioComponent;
class USoundWaveProcedural;
class UMaterialInterface;

struct AEGISWAR_API FWarAtmosphereMix
{
    float Nature=0, Weather=0, Work=0, Military=0;
};

namespace WarRegionalAtmosphere
{
    constexpr int32 SampleRate=24000;
    constexpr int32 MaximumParticles=192;
    AEGISWAR_API FWarAtmosphereMix Mix(float Village, float Frontage, float Daylight, float Weather, bool bInside, bool bCombat);
    AEGISWAR_API TArray<int16> Samples(FName Zone, int64 FirstSample, int32 Count, const FWarAtmosphereMix& Mix);
    AEGISWAR_API int32 ParticleCount(FName Zone, float Strength, bool bInside);
}

/** Opt-in local scenery effects. The authority clock selects conditions; this actor never changes gameplay or saves. */
UCLASS()
class AEGISWAR_API AWarRegionalAtmosphere : public AActor
{
    GENERATED_BODY()
public:
    AWarRegionalAtmosphere();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") FName ZoneId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") FVector VillageCentre=FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") TArray<FVector> MilitaryCentres;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") TArray<FVector> SteamSites;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") TObjectPtr<UMaterialInterface> WeatherMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere", meta=(ClampMin="0",ClampMax="1")) float AudioGain=.6f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UProceduralMeshComponent> WeatherMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UAudioComponent> Audio;
    UFUNCTION(BlueprintCallable, Category="Regional atmosphere") bool PreviewFrame(FVector Eye, FVector Forward, double Seconds, float Strength, bool bInside=false);
    UFUNCTION(BlueprintPure, Category="Regional atmosphere") int32 GetParticleCount() const { return VisibleParticles; }
    UFUNCTION(BlueprintPure, Category="Regional atmosphere") FString DescribeLocalState() const;
    /** Original synthesized preview bytes, not a recording of hardware playback. */
    UFUNCTION(BlueprintCallable, Category="Regional atmosphere") static TArray<uint8> AudioStudy(FName Zone, float Village, float Frontage, float Daylight, float Strength, bool bInside=false);
private:
    void DrawWeather(FVector Eye, FVector Forward, double Seconds, float Strength, bool bInside);
    void StopLocalEffects();
    bool InsideRoom(FVector Eye) const;
    UPROPERTY(Transient) TObjectPtr<USoundWaveProcedural> Wave;
    int32 VisibleParticles=0;
    int64 AudioSample=0;
    float RenderedStrength=0;
    FWarAtmosphereMix CurrentMix;
    bool bActive=false, bObserverInside=false;
};
