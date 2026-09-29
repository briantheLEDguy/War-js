#include "WarSiegeEquipment.h"
#include "WarSiegeGameMode.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "NavigationData.h"
#include "Net/UnrealNetwork.h"
#include "WarSiegeNavigation.h"
#include "WarPlayerState.h"
#include "EngineUtils.h"
#include "Engine/OverlapResult.h"

FRotator WarSiegeEquipment::SurfaceRotation(float Yaw,float ForwardGrade,float RightGrade)
{
    const float Pitch=FMath::Atan(ForwardGrade);
    // Preserve steering yaw while matching the floor's longitudinal and cross grades.
    return FRotator(FMath::RadiansToDegrees(Pitch),Yaw,
        -FMath::RadiansToDegrees(FMath::Atan(RightGrade*FMath::Cos(Pitch))));
}
ANavigationData* WarSiegeEquipment::Navigation(UWorld* World)
{
    auto* Nav=World ? FNavigationSystem::GetCurrent<UNavigationSystemV1>(World) : nullptr;
    auto* Data=Nav ? Nav->GetNavDataForProps(FNavAgentProperties(280,330)) : nullptr;
    // Never silently fall back to pedestrian clearance when the convoy bake is absent.
    return Data && Data->GetConfig().Name==TEXT("SiegeConvoy")
        && FMath::IsNearlyEqual(Data->GetConfig().AgentRadius,280.f) ? Data : nullptr;
}

bool UWarSiegeEquipmentDefinition::Validate(FString& Error) const
{
    if (!bReviewed || Parts.IsEmpty() || CrewPositions.Num()!=2 || SourceSha256.Len()!=64
        || HullExtent.ContainsNaN() || HullExtent.GetMin()<=0 || WalkSpeed<=0 || WheelCircumference<=0 || StrikeDuration<=0
        || !PushAnimation.LoadSynchronous() || !HoldAnimation.LoadSynchronous())
    { Error=TEXT("Siege equipment requires reviewed authored models and fitted engineer animations."); return false; }
    bool HasStrike=false;
    for (const auto& Part:Parts)
    {
        HasStrike |= Part.Strike.Num()>1;
        if (!Part.Mesh.LoadSynchronous() || Part.Roll.Num()<2)
    { Error=TEXT("A required siege equipment mesh or mechanical animation is missing."); return false; }
    }
    if (bBatteringRam && !HasStrike) { Error=TEXT("The battering ram has no authored strike."); return false; }
    return true;
}
AWarSiegeEquipment::AWarSiegeEquipment()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("EquipmentOrigin"));
    Hull=CreateDefaultSubobject<UBoxComponent>(TEXT("SweptHull")); Hull->SetupAttachment(RootComponent);
    Hull->SetRelativeLocation(FVector(0,0,155)); Hull->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Hull->SetCollisionObjectType(ECC_WorldDynamic); Hull->SetCollisionResponseToAllChannels(ECR_Block);
    Hull->SetCanEverAffectNavigation(false);
    bReplicates=true; bAlwaysRelevant=true; SetReplicateMovement(true); PrimaryActorTick.bCanEverTick=true;
    SetNetUpdateFrequency(20);
}
bool AWarSiegeEquipment::Initialize(UWarSiegeEquipmentDefinition* InDefinition)
{
    FString Error;
    if (!HasAuthority() || !InDefinition || !InDefinition->Validate(Error)) return false;
    Definition=InDefinition; Engineers.SetNum(2);Trail={GetActorLocation()};TrailLength=0;
    OnRep_Definition(); TryPlace(); ForceNetUpdate(); return Meshes.Num()==Definition->Parts.Num();
}
void AWarSiegeEquipment::OnRep_Definition()
{
    for (const auto& Mesh:Meshes) if (Mesh) Mesh->DestroyComponent(); Meshes.Reset();
    if (!Definition) return;
    Hull->SetBoxExtent(Definition->HullExtent);
    OnRep_Placed();
    for (const auto& Part:Definition->Parts)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(this); Mesh->SetupAttachment(RootComponent);
        Mesh->SetStaticMesh(Part.Mesh.LoadSynchronous()); Mesh->SetMobility(EComponentMobility::Movable);
        // The convoy uses an explicit swept hull. Render meshes do not carve navigation.
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mesh->SetCanEverAffectNavigation(false);
        Mesh->RegisterComponent(); Meshes.Add(Mesh);
    }
}
bool AWarSiegeEquipment::HasCrew() const
{
    if (!bPlaced || Engineers.Num()!=2) return false;
    for (const auto& Engineer:Engineers) if (!IsValid(Engineer) || Engineer->IsDead() || !Engineer->IsVisualReady()) return false;
    return true;
}
bool AWarSiegeEquipment::Ground(const FVector& At,FVector& Result) const
{
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeGround),false,this);
    for (const auto& Engineer:Engineers) Query.AddIgnoredActor(Engineer);
    if (!GetWorld()->LineTraceSingleByObjectType(Hit,At+FVector(0,0,300),At-FVector(0,0,500),FCollisionObjectQueryParams(ECC_WorldStatic),Query)
        // A wheel can contact a steep tessellated patch on an otherwise usable
        // ramp. Navigation and the swept hull constrain the route; the complete
        // support footprint determines chassis attitude, not one triangle.
        || Hit.ImpactNormal.Z<.2f)
    {
        if (FMath::Fmod(GetWorld()->GetTimeSeconds(),2.f)<.04f)
            UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_GROUND_FAILED %s sample=%s actor=%s point=%s normal=%s"),*GetName(),*At.ToString(),*GetNameSafe(Hit.GetActor()),*Hit.ImpactPoint.ToString(),*Hit.ImpactNormal.ToString());
        return false;
    }
    Result=Hit.ImpactPoint; return true;
}
FVector AWarSiegeEquipment::CrewPosition(int32 Seat) const
{
    if (!Definition || !Definition->CrewPositions.IsValidIndex(Seat)) return GetActorLocation();
    FVector Position=GetActorTransform().TransformPosition(Definition->CrewPositions[Seat]), Surface;
    if (Ground(Position,Surface)) Position.Z=Surface.Z;
    return Position;
}
FVector WarSiegeEquipment::TrailingPoint(TConstArrayView<FVector> Trail,float Distance)
{
    // Follow the route already travelled, including corners. A point directly
    // behind the current heading can lie inside a house during a turn.
    if (Trail.IsEmpty()) return FVector::ZeroVector;
    FVector Point=Trail.Last();Distance=FMath::Max(0.f,Distance);
    for (int32 I=Trail.Num()-2;I>=0;--I)
    {
        const float Segment=FVector::Dist2D(Point,Trail[I]);
        if (Segment>=Distance && Segment>0) return FMath::Lerp(Point,Trail[I],Distance/Segment);
        Distance-=Segment;Point=Trail[I];
    }
    return Point-FVector(Distance,0,0);
}
FVector AWarSiegeEquipment::TrailingLocation(float Distance) const
{ return Trail.IsEmpty() ? GetActorLocation()-FVector(Distance,0,0) : WarSiegeEquipment::TrailingPoint(Trail,Distance); }
bool AWarSiegeEquipment::BindEngineer(int32 Seat,AWarSiegeCharacter* Engineer)
{
    if (!HasAuthority() || !Engineers.IsValidIndex(Seat) || !Engineer || Engineer->IsDead()) return false;
    Engineers[Seat]=Engineer; Engineer->Equipment=this;
    // The always-relevant vehicle must never outlive its pushing crew on a client.
    Engineer->bAlwaysRelevant=true;Engineer->ForceNetUpdate();
    Engineer->GetCharacterMovement()->DisableMovement();
    Engineer->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    PlaceEngineers(); ForceNetUpdate(); return true;
}
void AWarSiegeEquipment::PlaceEngineers()
{
    for (int32 I=0;I<Engineers.Num();++I) if (auto* Engineer=Engineers[I].Get(); IsValid(Engineer) && !Engineer->IsDead())
    {
        // Character network smoothing must not move a seated grip away from its vehicle.
        Engineer->GetCharacterMovement()->NetworkSmoothingMode=ENetworkSmoothingMode::Disabled;
        Engineer->SetActorLocationAndRotation(CrewPosition(I)+GetActorQuat().RotateVector(FVector(0,0,Engineer->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())),
            GetActorRotation());
    }
}
void AWarSiegeEquipment::Stop() { bMoving=false; }
void AWarSiegeEquipment::Operate(bool bEnabled)
{
    const double Now=GetWorld()->GetTimeSeconds();
    if (!bEnabled || !HasCrew() || !Definition || !Definition->bBatteringRam) { StrikeStarted=-1; return; }
    if (StrikeStarted<0 || Now>=StrikeStarted+Definition->StrikeDuration+.7) StrikeStarted=Now;
}
bool AWarSiegeEquipment::Drive(const FVector& Destination,float Speed,float Delta)
{
    Stop();
    if (!HasAuthority() || RecoverOverlaps()) return false;
    if (!Definition || !HasCrew() || Speed<=0 || Delta<=0) { Operate(false);return false; }
    if (FVector::Dist2D(GetActorLocation(),Destination)<5) return true;
    // Reissuing an arrived escort goal must not restart the gate strike every tick.
    Operate(false);
    if (Route.IsEmpty() || FVector::DistSquared(RouteGoal,Destination)>10000)
    {
        auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()); FNavLocation End;
        auto* Data=WarSiegeEquipment::Navigation(GetWorld());
        // A following point can lie below the ramp at a slope transition.
        // Project its horizontal position onto the actual route before pathfinding.
        if (!Nav || !Data || !Nav->ProjectPointToNavigation(Destination,End,FVector(100,100,1200),Data)) return false;
        auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(),GetActorLocation(),End.Location,Data);
        if (!Path || !Path->IsValid() || Path->IsPartial()) return false;
        Route=Path->PathPoints; RouteGoal=Destination;
    }
    while (Route.Num()>1 && FVector::Dist2D(GetActorLocation(),Route[0])<80) Route.RemoveAt(0);
    const FVector Direction=(Route[0]-GetActorLocation()).GetSafeNormal2D();
    FRotator Rotation=GetActorRotation();
    Rotation.Yaw=FMath::FixedTurn(Rotation.Yaw,Direction.Rotation().Yaw,35*Delta);
    FVector Position=GetActorLocation();
    if (FMath::Abs(FMath::FindDeltaAngleDegrees(Rotation.Yaw,Direction.Rotation().Yaw))<8)
        Position+=Direction*FMath::Min(Speed*Delta,FVector::Dist2D(Position,Route[0]));
    if (!GroundPose(Position,Rotation) || !MovementClear(Position,Rotation)) return false;
    const float Distance=FVector::Dist2D(GetActorLocation(),Position);
    SetActorLocationAndRotation(Position,Rotation); Travel+=Distance; bMoving=Distance>.01f; PlaceEngineers();
    if (Distance>.01f)
    {
        Trail.Add(Position);TrailLength+=Distance;
        while (Trail.Num()>2 && TrailLength>2000)
        { TrailLength-=FVector::Dist2D(Trail[0],Trail[1]);Trail.RemoveAt(0); }
    }
    return FVector::Dist2D(Position,Destination)<5;
}
bool AWarSiegeEquipment::GroundPose(FVector& Position, FRotator& Rotation) const
{
    FVector Surface;
    if (!Ground(Position,Surface)) return false;
    const FRotator Heading(0,Rotation.Yaw,0);
    const FVector Support=Definition->HullExtent;
    FVector Corners[4],Floors[4];
    for (int32 I=0;I<4;++I)
    {
        Corners[I]=FVector(I<2 ? Support.X : -Support.X,I%2 ? Support.Y : -Support.Y,0);
        if (!Ground(Position+Heading.RotateVector(Corners[I]),Floors[I])) return false;
    }
    // Fit both grades across the full chassis. The retained street has a cross
    // slope as well as an uphill ramp; pitch alone drives one wheel into it.
    const float ForwardGrade=(Floors[0].Z+Floors[1].Z-Floors[2].Z-Floors[3].Z)/(4*Support.X);
    const float RightGrade=(Floors[1].Z+Floors[3].Z-Floors[0].Z-Floors[2].Z)/(4*Support.Y);
    // Preserve steering yaw: projecting a forward vector onto the plane also
    // changes yaw, which can prevent the convoy ever satisfying its turn limit.
    Rotation=WarSiegeEquipment::SurfaceRotation(Rotation.Yaw,ForwardGrade,RightGrade);
    Position.Z=Surface.Z;
    // Re-sample the actual rotated footprint, including its middle edges. A
    // tessellated street can rise between corner samples at a ramp transition.
    float Height=Surface.Z;
    for (int32 X=-1;X<=1;++X) for (int32 Y=-1;Y<=1;++Y)
    {
        const FVector Contact=Rotation.RotateVector(FVector(X*Support.X,Y*Support.Y,0));
        FVector Floor;
        if (!Ground(Position+Contact,Floor)) return false;
        Height=FMath::Max(Height,Floor.Z-Contact.Z);
    }
    Position.Z=Height;
    return true;
}
void AWarSiegeEquipment::OnRep_Placed()
{
    const bool Ready=bPlaced && Definition;
    Hull->SetCollisionEnabled(Ready ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
    SetActorHiddenInGame(!Ready);
}
bool AWarSiegeEquipment::PoseClear(const FVector& Position,const FQuat& Rotation,float Margin) const
{
    if (!Definition) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegePlacement),false,this);
    for (const auto& Engineer:Engineers) Query.AddIgnoredActor(Engineer);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
    return !GetWorld()->OverlapAnyTestByObjectType(Position+Rotation.RotateVector(FVector(0,0,155)),Rotation,
        Objects,FCollisionShape::MakeBox(Definition->HullExtent+FVector(Margin)),Query);
}
bool AWarSiegeEquipment::TryPlace()
{
    if (!HasAuthority() || !Definition) return false;
    if (bPlaced) return true;
    Hull->SetBoxExtent(Definition->HullExtent);
    FVector Position=GetActorLocation(); FRotator Rotation=GetActorRotation();
    if (!GroundPose(Position,Rotation) || !PoseClear(Position,Rotation.Quaternion(),3)) return false;
    SetActorLocationAndRotation(Position,Rotation); Trail={Position};
    bPlaced=true; OnRep_Placed(); ForceNetUpdate(); return true;
}
bool AWarSiegeEquipment::MovementClear(const FVector& Position,const FRotator& Rotation) const
{
    // Enclose each rotational arc, not just its endpoints. The inflated box is
    // conservative by the maximum distance any hull corner travels per sample.
    const FQuat From=GetActorQuat(), To=Rotation.Quaternion();
    const float Reach=Definition->HullExtent.Size()+155;
    const float Angle=From.AngularDistance(To);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt((Angle*Reach+FVector::Distance(GetActorLocation(),Position))/5));
    const float Margin=3+Angle*Reach/Steps;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeMovement),false,this);
    for (const auto& Engineer:Engineers) Query.AddIgnoredActor(Engineer);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
    for (int32 I=1;I<=Steps;++I)
    {
        const float A=float(I-1)/Steps,B=float(I)/Steps;
        const FQuat Q=FQuat::Slerp(From,To,B);
        const FVector Start=FMath::Lerp(GetActorLocation(),Position,A)+FQuat::Slerp(From,To,A).RotateVector(FVector(0,0,155));
        const FVector End=FMath::Lerp(GetActorLocation(),Position,B)+Q.RotateVector(FVector(0,0,155));
        FHitResult Hit;
        if (GetWorld()->SweepSingleByObjectType(Hit,Start,End,Q,Objects,
            FCollisionShape::MakeBox(Definition->HullExtent+FVector(Margin)),Query)) return false;
    }
    return true;
}
bool AWarSiegeEquipment::RecoverOverlaps()
{
    if (!HasAuthority() || !bPlaced) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeRecovery),false,this);
    for (const auto& Engineer:Engineers) Query.AddIgnoredActor(Engineer);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Hull->GetComponentLocation(),Hull->GetComponentQuat(),
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Definition->HullExtent),Query);
    bool Blocked=false;
    for (const auto& Hit:Overlaps)
    {
        auto* Pawn=Cast<AWarCharacter>(Hit.GetActor());
        if (!Pawn || Pawn->IsDead()) continue;
        Blocked=true; Stop(); Operate(false);
        auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
        const auto* Capsule=Pawn->GetCapsuleComponent();
        const auto* Data=Nav ? Nav->GetNavDataForProps(Pawn->GetNavAgentPropertiesRef()) : nullptr;
        bool Recovered=false;
        for (float Ring:{400.f,600.f,900.f,1200.f})
        {
            for (int32 I=0;I<16 && !Recovered;++I)
            {
                const float Angle=I*PI/8;
                FNavLocation Floor; FVector Center;
                if (Nav && Data && Nav->ProjectPointToNavigation(Pawn->GetActorLocation()+FVector(FMath::Cos(Angle)*Ring,FMath::Sin(Angle)*Ring,0),Floor,FVector(80,80,500),Data)
                    && WarSiegeNavigation::SpawnCandidate(GetWorld(),Floor.Location,Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight(),Center))
                    Recovered=Pawn->TeleportTo(Center,Pawn->GetActorRotation(),false,true);
            }
            if (Recovered) break;
        }
        if (!Recovered) if (auto* Mode=GetWorld()->GetAuthGameMode<AWarSiegeGameMode>(); Mode && Mode->Battlefield)
        {
            const auto* PS=Pawn->GetPlayerState<AWarPlayerState>();
            const int32 Index=Mode->SiegeState()->Siege.Stage*2+(PS && PS->GetRealm()==EWarRealm::Riftbound ? 1 : 0);
            FVector Center;
            if (WarSiegeNavigation::SpawnCenter(GetWorld(),Mode->Battlefield->TeamSpawns[Index],Center))
                Recovered=Pawn->TeleportTo(Center,Pawn->GetActorRotation(),false,true);
        }
        if (Recovered) { Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->ForceNetUpdate(); }
    }
    return Blocked;
}
void AWarSiegeEquipment::UpdateEscapeCollision()
{
    // A correction can place a capsule inside the hull on either peer. Permit
    // escape through this engine only until clear, even if no teleport is safe.
    TSet<TWeakObjectPtr<AWarCharacter>> Inside;
    if (bPlaced)
    {
        TArray<FOverlapResult> Hits;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeEscape),false,this);
        for (const auto& Engineer:Engineers) Query.AddIgnoredActor(Engineer);
        GetWorld()->OverlapMultiByObjectType(Hits,Hull->GetComponentLocation(),Hull->GetComponentQuat(),
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Definition->HullExtent),Query);
        for (const auto& Hit:Hits) if (auto* Pawn=Cast<AWarCharacter>(Hit.GetActor()))
        { Inside.Add(Pawn);Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(this,true); }
    }
    for (const auto& Pawn:EscapingPawns) if (Pawn.IsValid() && !Inside.Contains(Pawn))
        Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(this,false);
    EscapingPawns=MoveTemp(Inside);
}
bool AWarSiegeEquipment::CrewAnimation(UAnimSequence*& Clip,float& Time) const
{
    if (!Definition) return false;
    Clip=bMoving ? Definition->PushAnimation.LoadSynchronous() : Definition->HoldAnimation.LoadSynchronous();
    if (!Clip) return false;
    Time=bMoving ? FMath::Fmod(Travel/FMath::Max(1.f,Definition->WalkSpeed),Clip->GetPlayLength()) : 0;
    return true;
}
void AWarSiegeEquipment::Tick(float Delta)
{
    Super::Tick(Delta); if (!Definition) return;
    if (HasAuthority()) RecoverOverlaps();
    UpdateEscapeCollision();
    PlaceEngineers();
    if (HasAuthority() && !HasCrew()) { Stop(); Operate(false); }
    const auto* GS=GetWorld()->GetGameState(); const double Now=GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
    for (int32 I=0;I<Meshes.Num();++I)
    {
        const auto& Part=Definition->Parts[I]; const bool Strike=StrikeStarted>=0 && Definition->bBatteringRam && !Part.Strike.IsEmpty();
        const auto& Frames=Strike ? Part.Strike : Part.Roll; if (Frames.IsEmpty()) continue;
        const float Phase=Strike ? FMath::Clamp(float((Now-StrikeStarted)/Definition->StrikeDuration),0.f,1.f)
            : FMath::Fmod(Travel/Definition->WheelCircumference,1.f);
        const float Frame=Phase*(Frames.Num()-1); const int32 A=FMath::FloorToInt(Frame),B=FMath::Min(A+1,Frames.Num()-1);
        FTransform Pose; Pose.Blend(Frames[A],Frames[B],Frame-A); Meshes[I]->SetRelativeTransform(Pose);
    }
}
void AWarSiegeEquipment::EndPlay(const EEndPlayReason::Type Reason)
{
    for (const auto& Pawn:EscapingPawns) if (Pawn.IsValid()) Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(this,false);
    for (const auto& Engineer:Engineers) if (IsValid(Engineer)) Engineer->Equipment=nullptr;
    Super::EndPlay(Reason);
}
void AWarSiegeEquipment::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AWarSiegeEquipment,Definition); DOREPLIFETIME(AWarSiegeEquipment,bPlaced);
    DOREPLIFETIME(AWarSiegeEquipment,Engineers); DOREPLIFETIME(AWarSiegeEquipment,Travel);
    DOREPLIFETIME(AWarSiegeEquipment,bMoving); DOREPLIFETIME(AWarSiegeEquipment,StrikeStarted);
}
