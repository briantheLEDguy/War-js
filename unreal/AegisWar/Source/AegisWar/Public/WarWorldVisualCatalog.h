#pragma once
#include "CoreMinimal.h"

/** Exact reviewed component binding. Package location alone never admits a model. */
struct AEGISWAR_API FWarWorldVisualBinding
{
    FName Zone;
    FName Entity;
    FName VisualProp;
    FName Purpose;
    FString SourceModel;
    FString SourceSha256;
    FString Mesh;
    TArray<FString> Materials;
    FName CollisionProfile;
};

namespace WarWorldVisuals
{
    AEGISWAR_API FString Key(FName Purpose, FName Zone, FName Entity);
    AEGISWAR_API bool Parse(const FString& Json, const FString& ContentSha256,
        TMap<FString, FWarWorldVisualBinding>& Bindings, FString& Error);
    AEGISWAR_API bool Matches(const FWarWorldVisualBinding& Binding, FName VisualProp,
        const FString& Mesh, const TArray<FString>& Materials, FName CollisionProfile);
}
