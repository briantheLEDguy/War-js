#pragma once
#include "CoreMinimal.h"

class UWorld;
class AActor;
class AWarCharacter;
class FJsonObject;
class UStaticMeshComponent;

namespace WarCitadelLightingWitness
{
    /** Read-only game-thread state at screenshot request; not a renderer acceptance receipt. */
    TSharedPtr<FJsonObject> Capture(UWorld* World, const AWarCharacter* Pawn, const AActor* Camera);
    /** Actual loaded backdrop controls; visual and renderer acceptance stay separate. */
    TSharedPtr<FJsonObject> CaptureBackdrop(const UStaticMeshComponent* Component);
    /** Component bindings and effective render proxies; does not identify actual submitted mesh batches or pixels. */
    TArray<TSharedPtr<FJsonObject>> CapturePrivateSurfaceMaterials(const UStaticMeshComponent* Component);
    /** A valid fallback shader map cannot make the requested private material ready. */
    bool PrivateMaterialResourceReady(bool ExpectedInterface, bool UsedFallback, bool ShaderMapValid);
    /** Existing study surfaces plus the exact owned mountain instance name; does not grant readiness. */
    bool PrivateSurfaceMaterialPath(const FString& Path);
    TSharedPtr<FJsonObject> PrivateMaterialReadiness(UWorld* World);
}
