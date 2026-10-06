#pragma once
#include "WarCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "GameFramework/CharacterMovementComponent.h"

/** Receipt policy for the unchanged UE 5.8 native character, never a physics override. */
namespace WarCitadelCapsulePolicy
{
    inline TArray<TSharedPtr<FJsonValue>> Responses(const UCapsuleComponent* Capsule)
    {
        TArray<TSharedPtr<FJsonValue>> Values;
        const auto& Response=Capsule->GetCollisionResponseToChannels();
        static_assert(UE_ARRAY_COUNT(Response.EnumArray)==64,"Review the native collision policy after an engine change");
        for (const uint8 Value:Response.EnumArray) Values.Add(MakeShared<FJsonValueNumber>(Value));
        return Values;
    }
    inline bool Expected(const UCapsuleComponent* Capsule)
    {
        if (!Capsule || Capsule->GetCollisionProfileName()!=FName(TEXT("Custom"))
            || Capsule->GetCollisionEnabled()!=ECollisionEnabled::QueryAndPhysics
            || Capsule->GetCollisionObjectType()!=ECC_Pawn || Capsule->IsSimulatingPhysics()) return false;
        const auto& Response=Capsule->GetCollisionResponseToChannels();
        // The inherited Pawn profile ignores the engine gizmo; WarCharacter's
        // existing visibility override blocks that channel and names it Custom.
        for (int32 I=0;I<UE_ARRAY_COUNT(Response.EnumArray);++I)
            if (Response.EnumArray[I]!=(I==int32(ECC_EngineTraceChannel1) ? ECR_Ignore : ECR_Block)) return false;
        return true;
    }
    inline bool ExpectedKinematics(const AWarCharacter* Pawn)
    {
        const auto* Capsule=Pawn ? Pawn->GetCapsuleComponent() : nullptr;
        const auto* Movement=Pawn ? Pawn->GetCharacterMovement() : nullptr;
        return Capsule && Movement && Movement->UpdatedComponent==Capsule
            && Capsule->GetUnscaledCapsuleRadius()==42.f && Capsule->GetUnscaledCapsuleHalfHeight()==96.f
            && Capsule->GetScaledCapsuleRadius()==42.f && Capsule->GetScaledCapsuleHalfHeight()==96.f
            && Capsule->GetComponentScale().Equals(FVector::OneVector,1e-10)
            && Capsule->GetComponentQuat().GetUpVector().Equals(FVector::UpVector,1e-10)
            && Movement->MaxStepHeight==45.f
            && (Pawn->HasAnyFlags(RF_ClassDefaultObject) ? Movement->GetWalkableFloorZ()==.71f
                : FMath::IsNearlyEqual(Movement->GetWalkableFloorZ(),.71f,1e-7f))
            && Movement->GravityScale==1.f && Movement->GetGravityDirection().Equals(FVector(0,0,-1),1e-10);
    }
    inline bool Matches(const AWarCharacter* Pawn)
    {
        const auto* Default=GetDefault<AWarCharacter>();
        if (!Pawn || Pawn->GetClass()!=AWarCharacter::StaticClass() || !Pawn->GetActorEnableCollision()
            || !Default || !Default->GetActorEnableCollision()) return false;
        const auto* Actual=Pawn->GetCapsuleComponent();const auto* Original=Default->GetCapsuleComponent();
        // Independently enforce the reviewed policy on both sides: two equally
        // altered capsules must not masquerade as an unchanged class default.
        if (!Expected(Actual) || !Expected(Original) || !ExpectedKinematics(Pawn) || !ExpectedKinematics(Default)) return false;
        if (Pawn->GetCharacterMovement()->MaxStepHeight!=Default->GetCharacterMovement()->MaxStepHeight
            || !FMath::IsNearlyEqual(Pawn->GetCharacterMovement()->GetWalkableFloorZ(),Default->GetCharacterMovement()->GetWalkableFloorZ(),1e-7f)) return false;
        const auto& A=Actual->GetCollisionResponseToChannels();const auto& B=Original->GetCollisionResponseToChannels();
        for (int32 I=0;I<UE_ARRAY_COUNT(A.EnumArray);++I) if (A.EnumArray[I]!=B.EnumArray[I]) return false;
        return true;
    }
    inline TSharedRef<FJsonObject> Readback(const AWarCharacter* Pawn)
    {
        auto Row=MakeShared<FJsonObject>();const auto* Default=GetDefault<AWarCharacter>();
        const auto* Actual=Pawn->GetCapsuleComponent();const auto* Original=Default->GetCapsuleComponent();
        Row->SetNumberField(TEXT("version"),1);
        Row->SetStringField(TEXT("source"),TEXT("native_AWarCharacter_class_default_capsule_v1"));
        Row->SetStringField(TEXT("characterClass"),Pawn->GetClass()->GetPathName());
        Row->SetStringField(TEXT("classDefaultClass"),Default->GetClass()->GetPathName());
        Row->SetStringField(TEXT("profile"),Actual->GetCollisionProfileName().ToString());
        Row->SetStringField(TEXT("classDefaultProfile"),Original->GetCollisionProfileName().ToString());
        Row->SetNumberField(TEXT("collisionEnabled"),int32(Actual->GetCollisionEnabled()));
        Row->SetNumberField(TEXT("classDefaultCollisionEnabled"),int32(Original->GetCollisionEnabled()));
        Row->SetNumberField(TEXT("objectChannel"),int32(Actual->GetCollisionObjectType()));
        Row->SetNumberField(TEXT("classDefaultObjectChannel"),int32(Original->GetCollisionObjectType()));
        Row->SetArrayField(TEXT("responses"),Responses(Actual));Row->SetArrayField(TEXT("classDefaultResponses"),Responses(Original));
        Row->SetBoolField(TEXT("simulatingPhysics"),Actual->IsSimulatingPhysics());
        Row->SetBoolField(TEXT("classDefaultSimulatingPhysics"),Original->IsSimulatingPhysics());
        Row->SetBoolField(TEXT("matchesClassDefault"),Matches(Pawn));
        return Row;
    }
    inline TSharedRef<FJsonObject> KinematicsReadback(const AWarCharacter* Pawn)
    {
        auto Row=MakeShared<FJsonObject>();const auto* Default=GetDefault<AWarCharacter>();
        const auto* Capsule=Pawn->GetCapsuleComponent();const auto* Original=Default->GetCapsuleComponent();
        const auto* Movement=Pawn->GetCharacterMovement();const auto* OriginalMovement=Default->GetCharacterMovement();
        const auto Vector=[](const FVector& V) { return TArray<TSharedPtr<FJsonValue>>{
            MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; };
        Row->SetNumberField(TEXT("version"),1);
        Row->SetStringField(TEXT("source"),TEXT("native_AWarCharacter_class_default_kinematics_v1"));
        Row->SetNumberField(TEXT("capsuleRadiusCm"),Capsule->GetUnscaledCapsuleRadius());
        Row->SetNumberField(TEXT("capsuleHalfHeightCm"),Capsule->GetUnscaledCapsuleHalfHeight());
        Row->SetNumberField(TEXT("classDefaultRadiusCm"),Original->GetUnscaledCapsuleRadius());
        Row->SetNumberField(TEXT("classDefaultHalfHeightCm"),Original->GetUnscaledCapsuleHalfHeight());
        Row->SetNumberField(TEXT("scaledRadiusCm"),Capsule->GetScaledCapsuleRadius());
        Row->SetNumberField(TEXT("scaledHalfHeightCm"),Capsule->GetScaledCapsuleHalfHeight());
        Row->SetArrayField(TEXT("componentScale"),Vector(Capsule->GetComponentScale()));
        Row->SetArrayField(TEXT("capsuleAxis"),Vector(Capsule->GetComponentQuat().GetUpVector()));
        Row->SetNumberField(TEXT("maxStepHeightCm"),Movement->MaxStepHeight);
        Row->SetNumberField(TEXT("classDefaultMaxStepHeightCm"),OriginalMovement->MaxStepHeight);
        Row->SetNumberField(TEXT("walkableFloorZ"),Movement->GetWalkableFloorZ());
        Row->SetNumberField(TEXT("classDefaultWalkableFloorZ"),OriginalMovement->GetWalkableFloorZ());
        Row->SetNumberField(TEXT("gravityScale"),Movement->GravityScale);
        Row->SetNumberField(TEXT("classDefaultGravityScale"),OriginalMovement->GravityScale);
        Row->SetArrayField(TEXT("gravityDirection"),Vector(Movement->GetGravityDirection()));
        Row->SetBoolField(TEXT("updatedComponentIsCapsule"),Movement->UpdatedComponent==Capsule);
        Row->SetBoolField(TEXT("matchesClassDefault"),Matches(Pawn));
        return Row;
    }
    struct FKinematicsBaseline
    {
        TWeakObjectPtr<AWarCharacter> Avatar;
        float Radius,HalfHeight,StepHeight,FloorZ,ClassDefaultFloorZ;
        explicit FKinematicsBaseline(AWarCharacter* Pawn) : Avatar(Pawn),
            Radius(Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()),
            HalfHeight(Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
            StepHeight(Pawn->GetCharacterMovement()->MaxStepHeight),FloorZ(Pawn->GetCharacterMovement()->GetWalkableFloorZ()),
            ClassDefaultFloorZ(GetDefault<AWarCharacter>()->GetCharacterMovement()->GetWalkableFloorZ()) {}
        bool Matches(const AWarCharacter* Pawn) const
        {
            // Spawn initialization may round the native slope by one float ULP.
            // Once validated and captured, both live/default values stay exact.
            return Avatar.Get()==Pawn && WarCitadelCapsulePolicy::Matches(Pawn)
                && Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()==Radius
                && Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()==HalfHeight
                && Pawn->GetCharacterMovement()->MaxStepHeight==StepHeight
                && Pawn->GetCharacterMovement()->GetWalkableFloorZ()==FloorZ
                && GetDefault<AWarCharacter>()->GetCharacterMovement()->GetWalkableFloorZ()==ClassDefaultFloorZ;
        }
    };
}
